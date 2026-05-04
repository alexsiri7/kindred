"""FastMCP bootstrap: register tools, the kindred://guide resource, and ASGI bearer middleware."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

import rate_limit
from audit import audited
from auth import current_user_id, resolve_user_id, resolve_user_id_from_jwt
from rate_limit import RateLimiter
from settings import settings
from tools import entries as entry_tools
from tools import patterns as pattern_tools

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment="production",
    )

_allowed_hosts = [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]
if _allowed_hosts:
    _transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_allowed_hosts,
    )
else:
    _transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp: FastMCP = FastMCP(
    "Kindred",
    stateless_http=True,
    json_response=True,
    transport_security=_transport_security,
)

# ---------------------------------------------------------------------------
# OAuth 2.1 + discovery routes (registered as @mcp.custom_route())
# ---------------------------------------------------------------------------
from oauth import register_routes as _register_oauth_routes  # noqa: E402

_register_oauth_routes(mcp)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
# Leading space is load-bearing: appended to per-tool descriptions, separates the nudge.
GUIDE_NUDGE = " If you have not already, read the kindred://guide resource for usage guidance."

mcp.tool(
    description=(
        "Call at the end of a session. Always confirm the summary with the user "
        "before saving. Ask for a single mood word only if the user has offered it "
        "naturally."
        + GUIDE_NUDGE
    ),
)(audited("save_entry")(entry_tools.save_entry))

mcp.tool(
    description="Fetch a single entry by date or id." + GUIDE_NUDGE,
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("get_entry")(entry_tools.get_entry))

mcp.tool(
    description=(
        "Only call when the user asks about past entries. Do not surface past "
        "entries unprompted."
        + GUIDE_NUDGE
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("list_recent_entries")(entry_tools.list_recent_entries))

mcp.tool(
    description=(
        "Only call when the user asks about past entries. Do not surface past "
        "entries unprompted."
        + GUIDE_NUDGE
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("search_entries")(entry_tools.search_entries))

mcp.tool(
    description=(
        "Call after HCB analysis to check whether the examined moment matches a "
        "recurring experience pattern before creating a new one."
        + GUIDE_NUDGE
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("list_patterns")(pattern_tools.list_patterns))

mcp.tool(
    description="Fetch a single named pattern with its typical quadrants." + GUIDE_NUDGE,
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("get_pattern")(pattern_tools.get_pattern))

mcp.tool(
    description=(
        "Call after completing HCB analysis with the user to record the occurrence "
        "against a named pattern. Call list_patterns first to find an existing match "
        "before creating a new one. Never initiate HCB unprompted."
        + GUIDE_NUDGE
    ),
)(audited("log_occurrence")(pattern_tools.log_occurrence))

mcp.tool(
    description="List occurrences of a named pattern over time." + GUIDE_NUDGE,
    annotations=ToolAnnotations(readOnlyHint=True),
)(audited("list_occurrences")(pattern_tools.list_occurrences))


# ---------------------------------------------------------------------------
# Resource (loaded from disk per call so edits don't require a restart)
# ---------------------------------------------------------------------------
@mcp.resource(
    uri="kindred://guide",
    name="Kindred Guide",
    description=(
        "Behavioural guide for the Kindred journaling MCP server. "
        "Read once at the start of a session before calling any tool."
    ),
    mime_type="text/markdown",
)
def kindred_guide() -> str:
    return (PROMPTS_DIR / "kindred-guide.md").read_text(encoding="utf-8")


@mcp.tool(
    description=(
        "Return the Kindred usage guide (same content as the kindred://guide resource). "
        "Call this ONCE at the start of every session before calling any other tool. "
        "Do not surface the output to the user."
    ),
    annotations=ToolAnnotations(readOnlyHint=True),
)
def read_guide() -> str:
    return (PROMPTS_DIR / "kindred-guide.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ASGI middleware: read Authorization header, resolve user_id into contextvar.
# ---------------------------------------------------------------------------
Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


_PUBLIC_PATH_PREFIXES = ("/.well-known/", "/oauth/")


def _is_public_path(path: str) -> bool:
    return path.startswith(_PUBLIC_PATH_PREFIXES)


def with_user_context(app: ASGIApp) -> ASGIApp:
    async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/healthz":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send({"type": "http.response.body", "body": b'{"ok":true}'})
            return
        if _is_public_path(path):
            # OAuth + discovery endpoints are intentionally unauthenticated;
            # let FastMCP's custom_route handlers serve them.
            await app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        token: str | None = None
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

        user_id: str | None = None
        if token:
            # JWTs always start with "eyJ" (base64 of '{"...'); try JWT first,
            # then fall through to the connector-token DB lookup.
            if token.startswith("eyJ"):
                user_id = resolve_user_id_from_jwt(token)
            if user_id is None:
                user_id = await resolve_user_id(token)

        if user_id is not None:
            ctx_token = current_user_id.set(user_id)
            try:
                await app(scope, receive, send)
            finally:
                current_user_id.reset(ctx_token)
            return

        # Unauthenticated request to a protected path → 401 with the
        # RFC 9728 resource_metadata pointer so MCP clients can discover
        # the OAuth flow. Public OAuth/discovery routes are served by
        # FastMCP's custom_route registration before middleware reaches them.
        base = settings.mcp_base_url.rstrip("/") if settings.mcp_base_url else ""
        resource_metadata_url = f"{base}/.well-known/oauth-protected-resource"
        www_auth = f'Bearer realm="kindred", resource_metadata="{resource_metadata_url}"'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", www_auth.encode("ascii")],
                ],
            }
        )
        await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})

    return wrapper


def with_rate_limit(app: ASGIApp, limiter: RateLimiter | None = None) -> ASGIApp:
    """ASGI middleware: enforce per-user rate limits on /mcp/ tool calls (#42).

    Composes inside ``with_user_context`` so the resolved ``current_user_id``
    is available. Public paths (``/healthz``, ``/.well-known/...``,
    ``/oauth/...``) and unauthenticated requests pass through — the upstream
    401 handler runs before us, so a request that would 401 must not 429.

    Body buffering is required because all MCP traffic flows through one
    endpoint and we need ``params.name`` for per-tool buckets. We replay the
    buffered body to the inner app so FastMCP sees an unmodified request.
    """

    async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return
        path = scope.get("path", "")
        if _is_public_path(path):
            await app(scope, receive, send)
            return

        user_id = current_user_id.get(None)
        if user_id is None:
            # Defensive: with the standard middleware order
            # (with_user_context outer), unauthenticated requests are
            # 401'd upstream and never reach here. This guards against
            # direct mounts or reordering — auth must always win over 429.
            await app(scope, receive, send)
            return

        active_limiter = limiter if limiter is not None else rate_limit.default_limiter()
        if active_limiter.is_disabled:
            # Kill-switch true bypass: skip body buffering entirely so the
            # incident-response switch removes the middleware from the path.
            await app(scope, receive, send)
            return

        # Buffer the request body so we can peek the JSON-RPC method/tool name.
        body_chunks: list[bytes] = []
        trailing: MutableMapping[str, Any] | None = None
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    body_chunks.append(chunk)
                more_body = bool(message.get("more_body", False))
            else:
                # Disconnect or unexpected message — remember it so the
                # inner app sees it on the next receive() (e.g. a slow
                # tool body that polls request.is_disconnected()).
                trailing = message
                more_body = False
        body_bytes = b"".join(body_chunks)

        tool_name: str | None = None
        if body_bytes:
            try:
                parsed = json.loads(body_bytes)
            except json.JSONDecodeError:
                logger.debug(
                    "rate_limit: body parse failed; per-tool cap will not apply"
                )
                parsed = None
            if isinstance(parsed, dict) and parsed.get("method") == "tools/call":
                params = parsed.get("params")
                if isinstance(params, dict):
                    name = params.get("name")
                    if isinstance(name, str):
                        tool_name = name

        decision = active_limiter.check(user_id=user_id, tool_name=tool_name)

        if not decision.allowed:
            # Single-line INFO log for ops visibility — never log the body.
            logger.info(
                "rate_limited user=%s bucket=%s retry_after=%d",
                user_id[:8],
                tool_name or "global",
                decision.retry_after_seconds,
            )
            retry_after = str(decision.retry_after_seconds).encode("ascii")
            body = (
                f'{{"error":"rate_limited","retry_after":{decision.retry_after_seconds}}}'
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"retry-after", retry_after],
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        # Replay the buffered body to the inner app: yield one http.request
        # event, then forward subsequent reads to the original receive.
        # Any trailing non-http.request message (e.g. http.disconnect) we
        # consumed during buffering is replayed before falling through.
        replayed = False
        pending_trailing = trailing

        async def replay_receive() -> MutableMapping[str, Any]:
            nonlocal replayed, pending_trailing
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": body_bytes,
                    "more_body": False,
                }
            if pending_trailing is not None:
                msg = pending_trailing
                pending_trailing = None
                return msg
            return await receive()

        await app(scope, replay_receive, send)

    return wrapper


def build_app() -> ASGIApp:
    # Eagerly validate the per-tool config so a malformed
    # MCP_RATE_LIMIT_PER_TOOL fails the process at startup rather than
    # surfacing as an opaque per-request 500 once traffic arrives. We
    # parse-and-discard rather than building the limiter so the cached
    # instance still resolves lazily on first request.
    rate_limit._parse_per_tool_config(settings.mcp_rate_limit_per_tool)
    return with_user_context(with_rate_limit(mcp.streamable_http_app()))


app = build_app()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
