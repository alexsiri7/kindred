"""Per-user rate limiting for the MCP server (#42).

The MCP server has no rate limiting today, which lets a single client drive
unbounded ``search_entries`` calls (Requesty embed + pgvector RPC) — a real
cost and abuse risk in a multi-user deployment. This module supplies a
fixed-window in-memory ``RateLimiter`` keyed on ``(user_id, bucket)``: one
``__global__`` bucket per user covers all tool invocations, plus optional
per-tool buckets (default: ``search_entries`` 10/min) for the expensive
paths. Breaches surface as HTTP 429 with ``Retry-After`` from the ASGI
middleware in ``main.py``.

Fixed-window over token-bucket: the issue specifies "calls per minute"
which fixed windows describe natively, without floating-point refill rates.
The well-known fixed-window edge effect (up to 2× the cap at the boundary)
is acceptable here because we are bounding cost, not enforcing exactly-once
semantics.

Per-instance state (no Redis): the MCP server runs as a single Railway
service today, mirroring the precedent set by ``oauth_state.py``. Bounded
state + lock + lazy cleanup are copied directly from that module.

Future migration: swap to a Redis-backed limiter if/when we go multi-instance,
or to ``asyncio.Lock`` if profiling shows lock contention. Body buffering in
the middleware also assumes JSON-RPC request bodies (``json_response=True``,
``stateless_http=True`` on FastMCP today); a future SSE-style request stream
would need a streaming-aware buffer.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass

from settings import settings

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60
MAX_BUCKETS = 50_000
GLOBAL_BUCKET_KEY = "__global__"

# Lock protecting RateLimiter._buckets against concurrent access from
# threadpool-dispatched sync endpoints. Mirror of oauth_state._state_lock.
_lock = threading.Lock()


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


def _parse_per_tool_config(raw: str) -> dict[str, int]:
    """Parse ``"search_entries:10,foo:20"`` into ``{"search_entries":10,"foo":20}``.

    Empty / whitespace-only input → ``{}``. Malformed pair raises ``ValueError``
    so a misconfigured deployment fails loud at first request rather than
    silently degrading the cap.
    """
    out: dict[str, int] = {}
    if not raw or not raw.strip():
        return out
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if pair.count(":") != 1:
            raise ValueError(f"Malformed rate-limit pair {pair!r}; expected 'name:int'")
        name, limit_s = pair.split(":", 1)
        name = name.strip()
        limit_s = limit_s.strip()
        if not name:
            raise ValueError(f"Empty tool name in rate-limit pair {pair!r}")
        try:
            limit = int(limit_s)
        except ValueError as e:
            raise ValueError(
                f"Non-integer limit in rate-limit pair {pair!r}"
            ) from e
        out[name] = limit
    return out


class RateLimiter:
    """Thread-safe fixed-window per-user limiter.

    State: ``self._buckets[(user_id, key)] = [window_start_monotonic, count]``
    where ``key`` is ``GLOBAL_BUCKET_KEY`` or a tool name. We use a list
    rather than a dataclass for cheap in-place mutation under ``_lock``.
    """

    def __init__(
        self,
        global_per_min: int,
        per_tool: dict[str, int],
        disabled: bool,
    ) -> None:
        self._global_per_min = global_per_min
        self._per_tool = dict(per_tool)
        self._disabled = disabled
        self._buckets: dict[tuple[str, str], list[float]] = {}

    def check(self, user_id: str, tool_name: str | None) -> RateLimitDecision:
        """Decide whether to allow this call; increment buckets atomically on allow."""
        if self._disabled:
            return RateLimitDecision(True, 0)

        # Build the list of (key, limit) pairs to check. Skip the global
        # bucket entirely when global_per_min == 0 (operator opt-out) so we
        # don't even allocate a slot for it.
        checks: list[tuple[str, int]] = []
        if self._global_per_min > 0:
            checks.append((GLOBAL_BUCKET_KEY, self._global_per_min))
        if tool_name is not None and tool_name in self._per_tool:
            checks.append((tool_name, self._per_tool[tool_name]))

        if not checks:
            return RateLimitDecision(True, 0)

        with _lock:
            now = time.monotonic()

            if len(self._buckets) > MAX_BUCKETS:
                self._evict_expired_locked(now)
                if len(self._buckets) > MAX_BUCKETS:
                    # Fail-open: never block legitimate traffic for an
                    # internal bookkeeping issue. Visible in logs for ops.
                    logger.warning(
                        "rate_limit: bucket store at cap (%d), allowing request",
                        len(self._buckets),
                    )
                    return RateLimitDecision(True, 0)

            # Phase 1: check every bucket without mutating counts. If any
            # would breach, return without incrementing the others — the
            # atomicity invariant Task 2 GOTCHA spells out.
            biggest_retry = 0
            denied = False
            for key, limit in checks:
                bucket = self._buckets.get((user_id, key))
                if bucket is None or now - bucket[0] >= WINDOW_SECONDS:
                    # Either fresh or window expired — would reset on
                    # increment, so cannot deny here.
                    continue
                if bucket[1] >= limit:
                    denied = True
                    remaining = WINDOW_SECONDS - (now - bucket[0])
                    # math.ceil so 0.1s remaining -> 1, never 0; Retry-After
                    # parsers reject floats and clients tight-loop on 0.
                    retry = max(1, math.ceil(remaining))
                    if retry > biggest_retry:
                        biggest_retry = retry

            if denied:
                return RateLimitDecision(False, biggest_retry)

            # Phase 2: all checks pass — increment (or initialise) every
            # relevant bucket exactly once.
            for key, _limit in checks:
                bucket = self._buckets.get((user_id, key))
                if bucket is None or now - bucket[0] >= WINDOW_SECONDS:
                    self._buckets[(user_id, key)] = [now, 1]
                else:
                    bucket[1] += 1
            return RateLimitDecision(True, 0)

    def _evict_expired_locked(self, now: float) -> None:
        """Drop buckets whose window has fully elapsed. Caller holds ``_lock``."""
        expired = [
            k
            for k, bucket in self._buckets.items()
            if now - bucket[0] >= WINDOW_SECONDS
        ]
        for k in expired:
            del self._buckets[k]
        if expired:
            logger.debug("rate_limit: evicted %d expired buckets", len(expired))


_instance: RateLimiter | None = None


def build_default() -> RateLimiter:
    return RateLimiter(
        global_per_min=settings.mcp_rate_limit_global_per_min,
        per_tool=_parse_per_tool_config(settings.mcp_rate_limit_per_tool),
        disabled=settings.mcp_rate_limit_disabled,
    )


def default_limiter() -> RateLimiter:
    """Lazily build (and cache) the process-wide default limiter from settings."""
    global _instance
    if _instance is None:
        _instance = build_default()
    return _instance


def reset_for_tests() -> None:
    """Drop the cached default limiter so the next call re-reads settings."""
    global _instance
    _instance = None
