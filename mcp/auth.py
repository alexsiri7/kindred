"""Connector-token bearer auth for the MCP server.

PRD step 3 specifies a connector-token fallback while we defer MCP OAuth 2.1
(PRD step 8). Tokens are minted via the web app's ``POST /connect/token`` route
and pasted by the user into Claude.ai's connector config.

The user_id resolved from the bearer token is published into a
``contextvars.ContextVar`` by an ASGI middleware in ``main.py``, so tool bodies
can read ``current_user_id.get()`` without depending on internal SDK shape.

Future migration: replace ``ConnectorTokenVerifier`` with an OAuth 2.1
``AuthorizationServerProvider`` from ``mcp.server.auth`` once we ship step 8.
The ``TokenVerifier`` interface lets us swap without touching tool code.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar

from mcp.server.auth.provider import AccessToken, TokenVerifier

import db

current_user_id: ContextVar[str] = ContextVar("current_user_id")


class ConnectorTokenVerifier(TokenVerifier):
    """Look up bearer tokens in ``connector_tokens``; return AccessToken or None."""

    async def verify_token(self, token: str) -> AccessToken | None:
        # supabase-py is sync; wrap in to_thread so we don't block the loop.
        row = await asyncio.to_thread(db.lookup_connector_token, token)
        if row is None:
            return None
        return AccessToken(
            token=token,
            client_id=str(row["user_id"]),
            scopes=["user"],
            expires_at=None,
        )


async def resolve_user_id(token: str) -> str | None:
    """Used by the ASGI middleware to populate the contextvar."""
    row = await asyncio.to_thread(db.lookup_connector_token, token)
    if row is None:
        return None
    return str(row["user_id"])
