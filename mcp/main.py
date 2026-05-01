"""FastMCP bootstrap: register all 8 tools, 3 prompts, and ASGI bearer middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from auth import current_user_id, resolve_user_id
from tools import entries as entry_tools
from tools import patterns as pattern_tools

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

mcp: FastMCP = FastMCP(
    "Kindred",
    stateless_http=True,
    json_response=True,
)

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


def with_user_context(app: ASGIApp) -> ASGIApp:
    async def wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await app(scope, receive, send)
            return
        if scope.get("path") == "/healthz":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"application/json"]],
                }
            )
            await send({"type": "http.response.body", "body": b'{"ok":true}'})
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        token: str | None = None
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
        if token:
            user_id = await resolve_user_id(token)
            if user_id is not None:
                ctx_token = current_user_id.set(user_id)
                try:
                    await app(scope, receive, send)
                finally:
                    current_user_id.reset(ctx_token)
                return
        await app(scope, receive, send)

    return wrapper


def build_app() -> ASGIApp:
    return with_user_context(mcp.streamable_http_app())


app = build_app()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
