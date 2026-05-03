"""Unit tests for the per-user fixed-window rate limiter."""

from __future__ import annotations

from typing import Any

import pytest

import rate_limit
from rate_limit import RateLimiter, _parse_per_tool_config

USER_A = "user-a"
USER_B = "user-b"


def _make_clock(start: float = 1_000.0) -> tuple[list[float], Any]:
    """Return (current_time_box, getter). Mutate box[0] to advance the clock."""
    box = [start]

    def now() -> float:
        return box[0]

    return box, now


# ---------------------------------------------------------------------------
# Bucket arithmetic
# ---------------------------------------------------------------------------


def test_under_limit_allows() -> None:
    limiter = RateLimiter(global_per_min=60, per_tool={}, disabled=False)
    for _ in range(59):
        decision = limiter.check(USER_A, tool_name=None)
        assert decision.allowed is True
        assert decision.retry_after_seconds == 0


def test_over_limit_returns_429_decision() -> None:
    limiter = RateLimiter(global_per_min=60, per_tool={}, disabled=False)
    for _ in range(60):
        assert limiter.check(USER_A, tool_name=None).allowed is True
    decision = limiter.check(USER_A, tool_name=None)
    assert decision.allowed is False
    assert decision.retry_after_seconds >= 1
    assert decision.retry_after_seconds <= 60


def test_window_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    box, fake_now = _make_clock()
    monkeypatch.setattr(rate_limit.time, "monotonic", fake_now)
    limiter = RateLimiter(global_per_min=2, per_tool={}, disabled=False)
    assert limiter.check(USER_A, None).allowed is True
    assert limiter.check(USER_A, None).allowed is True
    assert limiter.check(USER_A, None).allowed is False
    box[0] += 61.0  # past the 60s window
    assert limiter.check(USER_A, None).allowed is True


def test_per_tool_independent() -> None:
    limiter = RateLimiter(
        global_per_min=1000, per_tool={"search_entries": 10}, disabled=False
    )
    for _ in range(10):
        assert limiter.check(USER_A, "search_entries").allowed is True
    assert limiter.check(USER_A, "search_entries").allowed is False
    # Other tool / global path not affected by the per-tool exhaustion.
    assert limiter.check(USER_A, "list_recent_entries").allowed is True


def test_per_tool_breach_does_not_consume_global() -> None:
    """Atomic-increment correctness: per-tool denial must not bump global count."""
    limiter = RateLimiter(
        global_per_min=2, per_tool={"search_entries": 1}, disabled=False
    )
    # Allowed: global=1, search=1.
    assert limiter.check(USER_A, "search_entries").allowed is True
    # Per-tool breach. With correct atomicity, global stays at 1; if broken,
    # it would have ticked to 2 and the next non-search call would fail.
    denied = limiter.check(USER_A, "search_entries")
    assert denied.allowed is False
    # If atomicity correct, global has 1 slot left → this call must pass.
    assert limiter.check(USER_A, "list_recent_entries").allowed is True
    # Now global is at cap (2/2).
    assert limiter.check(USER_A, "list_recent_entries").allowed is False


def test_users_are_isolated() -> None:
    limiter = RateLimiter(global_per_min=2, per_tool={}, disabled=False)
    assert limiter.check(USER_A, None).allowed is True
    assert limiter.check(USER_A, None).allowed is True
    assert limiter.check(USER_A, None).allowed is False
    # User B still has full budget.
    assert limiter.check(USER_B, None).allowed is True
    assert limiter.check(USER_B, None).allowed is True


def test_disabled_flag_no_ops() -> None:
    limiter = RateLimiter(global_per_min=1, per_tool={"x": 1}, disabled=True)
    for _ in range(1000):
        assert limiter.check(USER_A, "x").allowed is True


def test_global_zero_disables_global_only() -> None:
    limiter = RateLimiter(
        global_per_min=0, per_tool={"search_entries": 2}, disabled=False
    )
    # No global cap; many non-search calls all allowed.
    for _ in range(100):
        assert limiter.check(USER_A, "list_recent_entries").allowed is True
    # Per-tool cap still applies.
    assert limiter.check(USER_A, "search_entries").allowed is True
    assert limiter.check(USER_A, "search_entries").allowed is True
    assert limiter.check(USER_A, "search_entries").allowed is False


def test_retry_after_at_least_one(monkeypatch: pytest.MonkeyPatch) -> None:
    box, fake_now = _make_clock()
    monkeypatch.setattr(rate_limit.time, "monotonic", fake_now)
    limiter = RateLimiter(global_per_min=1, per_tool={}, disabled=False)
    assert limiter.check(USER_A, None).allowed is True
    # Advance to within 0.1s of window expiry; retry_after should still be >=1.
    box[0] += 59.9
    decision = limiter.check(USER_A, None)
    assert decision.allowed is False
    assert decision.retry_after_seconds >= 1


# ---------------------------------------------------------------------------
# _parse_per_tool_config
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a:10,b:20", {"a": 10, "b": 20}),
        ("", {}),
        ("   ", {}),
        ("  search_entries:10  ", {"search_entries": 10}),
        ("a:1,,b:2", {"a": 1, "b": 2}),  # blank pair tolerated
    ],
)
def test_parse_per_tool_config_valid(raw: str, expected: dict[str, int]) -> None:
    assert _parse_per_tool_config(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "a:not_an_int",
        "no_colon_at_all",
        ":10",  # empty name
        "a:1:extra",  # too many colons
    ],
)
def test_parse_per_tool_config_malformed_raises(raw: str) -> None:
    with pytest.raises(ValueError):
        _parse_per_tool_config(raw)


# ---------------------------------------------------------------------------
# Module-level default limiter helpers
# ---------------------------------------------------------------------------


def test_default_limiter_caches_and_reset_for_tests() -> None:
    rate_limit.reset_for_tests()
    first = rate_limit.default_limiter()
    second = rate_limit.default_limiter()
    assert first is second
    rate_limit.reset_for_tests()
    third = rate_limit.default_limiter()
    assert third is not first


# ---------------------------------------------------------------------------
# MAX_BUCKETS safety valve: lazy eviction + fail-open
# ---------------------------------------------------------------------------


def test_max_buckets_evicts_stale_then_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When at-cap, expired buckets are evicted on the next check and
    the request goes through normally."""
    monkeypatch.setattr(rate_limit, "MAX_BUCKETS", 5)
    box, fake_now = _make_clock()
    monkeypatch.setattr(rate_limit.time, "monotonic", fake_now)

    limiter = RateLimiter(global_per_min=10, per_tool={}, disabled=False)
    # Stuff the bucket dict with stale entries (window already expired).
    for i in range(10):
        limiter._buckets[(f"stale-user-{i}", rate_limit.GLOBAL_BUCKET_KEY)] = [
            box[0] - 120.0,  # well outside WINDOW_SECONDS
            1,
        ]
    assert len(limiter._buckets) == 10  # > MAX_BUCKETS

    decision = limiter.check(USER_A, tool_name=None)
    assert decision.allowed is True
    assert len(limiter._buckets) <= 5


def test_max_buckets_fail_open_when_eviction_cant_free(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When at-cap with no stale entries, allow + WARNING log (fail-open).

    The fail-open is a deliberate design choice — under stress we prefer
    availability over correctness. This pins that contract.
    """
    monkeypatch.setattr(rate_limit, "MAX_BUCKETS", 5)
    box, fake_now = _make_clock()
    monkeypatch.setattr(rate_limit.time, "monotonic", fake_now)

    limiter = RateLimiter(global_per_min=10, per_tool={}, disabled=False)
    # All-fresh entries — eviction will free nothing.
    for i in range(10):
        limiter._buckets[(f"fresh-user-{i}", rate_limit.GLOBAL_BUCKET_KEY)] = [
            box[0],
            1,
        ]

    with caplog.at_level("WARNING", logger="rate_limit"):
        decision = limiter.check(USER_A, tool_name=None)
    assert decision.allowed is True
    assert decision.retry_after_seconds == 0
    assert any("bucket store at cap" in r.getMessage() for r in caplog.records)
