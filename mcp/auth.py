"""Bearer auth: try kindred-issued JWT (in-memory) first, fall back to
connector-token DB lookup. JWT path enforces RFC 8707 audience binding."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar

from mcp.server.auth.provider import AccessToken, TokenVerifier

import db
from oauth.state import canonical_resource_url, verify_access_jwt

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
    """Connector-token DB lookup. Returns the user_id or None."""
    row = await asyncio.to_thread(db.lookup_connector_token, token)
    if row is None:
        return None
    return str(row["user_id"])


def resolve_user_id_from_jwt(token: str) -> str | None:
    """Verify a kindred-issued HS256 JWT bound to this server's canonical URL.

    Returns the ``sub`` claim (user_id) or ``None`` if verification fails for
    any reason (no secret, expired, bad signature, audience mismatch, malformed).
    Failures are intentionally swallowed so the middleware can fall back to
    the connector-token DB lookup.
    """
    return verify_access_jwt(token, expected_audience=canonical_resource_url())
