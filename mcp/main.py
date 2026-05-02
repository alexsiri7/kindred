"""FastMCP bootstrap: register all 8 tools, 3 prompts, and ASGI bearer middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

import sentry_sdk
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from auth import current_user_id, resolve_user_id, resolve_user_id_from_jwt
from oauth import register_routes as _register_oauth_routes
from oauth.state import base_url
from settings import settings
from tools import entries as entry_tools
from tools import patterns as pattern_tools

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

# OAuth 2.1 + discovery routes (RFC 9728/8414/7591/8707) — registered via
# mcp.custom_route() so they bypass FastMCP's authorization layer.
_register_oauth_routes(mcp)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
mcp.tool()(entry_tools.save_entry)
mcp.tool()(entry_tools.get_entry)
mcp.tool()(entry_tools.list_recent_entries)
mcp.tool()(entry_tools.search_entries)

mcp.tool()(pattern_tools.list_patterns)
mcp.tool()(pattern_tools.get_pattern)
mcp.tool()(pattern_tools.log_occurrence)
mcp.tool()(pattern_tools.list_occurrences)


# ---------------------------------------------------------------------------
# Prompts (loaded from disk per call so edits don't require a restart)
# ---------------------------------------------------------------------------
@mcp.prompt(title="Kindred — Start session")
def kindred_start() -> str:
    return (PROMPTS_DIR / "kindred-start.md").read_text(encoding="utf-8")


@mcp.prompt(title="Kindred — Hot Cross Bun")
def kindred_hcb() -> str:
    return (PROMPTS_DIR / "kindred-hcb.md").read_text(encoding="utf-8")


@mcp.prompt(title="Kindred — Close session")
def kindred_close() -> str:
    return (PROMPTS_DIR / "kindred-close.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ASGI middleware: read Authorization header, resolve user_id into contextvar.
# ---------------------------------------------------------------------------
Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


_PUBLIC_PATHS = frozenset(
    {
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-authorization-server",
        "/oauth/register",
        "/oauth/authorize",
        "/oauth/callback",
        "/oauth/token",
    }
)


def _bearer_token(scope: Scope) -> str | None:
    for k, v in scope.get("headers", []):
        if k == b"authorization":
            auth: str = v.decode("latin-1")
            if auth[:7].lower() == "bearer ":
                return auth[7:].strip()
            return None
    return None


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
        if path in _PUBLIC_PATHS:
            await app(scope, receive, send)
            return
        token = _bearer_token(scope)

        user_id: str | None = None
        if token:
            # Cheap heuristic: JWT base64 header always starts with "eyJ" — try
            # in-memory JWT verify first, fall back to connector-token DB lookup.
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

        # 401 with RFC 9728 resource_metadata pointer so MCP clients can
        # discover the OAuth flow. WWW-Authenticate MUST be absolute (#46539).
        resource_metadata_url = f"{base_url()}/.well-known/oauth-protected-resource"
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
        await send({"type": "http.response.body", "body": b'{"error":"invalid_token"}'})

    return wrapper


def build_app() -> ASGIApp:
    return with_user_context(mcp.streamable_http_app())


app = build_app()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
