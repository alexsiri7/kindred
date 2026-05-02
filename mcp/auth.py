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
import logging
from contextvars import ContextVar

import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

import db
from settings import settings

logger = logging.getLogger(__name__)

current_user_id: ContextVar[str] = ContextVar("current_user_id")

_warned_missing_secret = False


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


def resolve_user_id_from_jwt(token: str) -> str | None:
    """Decode a kindred-issued HS256 JWT signed with ``settings.secret_key``.

    Returns the ``sub`` claim (user_id) or ``None`` if verification fails for
    any reason (missing secret, expired token, bad signature, malformed payload).
    """
    global _warned_missing_secret
    if not settings.secret_key:
        if not _warned_missing_secret:
            logger.warning(
                "JWT auth attempted but SECRET_KEY is not configured; "
                "all JWT-bearing requests will fall through to connector-token lookup"
            )
            _warned_missing_secret = True
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.debug("JWT decode: expired token")
        return None
    except jwt.PyJWTError as exc:
        logger.debug("JWT decode failed: %s: %s", type(exc).__name__, exc)
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None
