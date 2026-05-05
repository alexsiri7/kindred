"""Connector-token lifecycle.

Tokens are minted by the web app's ``POST /connect/token`` endpoint and
looked up by the MCP server's auth middleware. Tokens carry an
``expires_at`` (default 90 days, configurable via
``CONNECTOR_TOKEN_TTL_DAYS``), a ``last_used_at`` stamp, and a
``revoked_at`` flag. The lookup RPC filters expired/revoked rows so the
MCP layer transparently sees them as 401s.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from lib import db
from lib.settings import settings as lib_settings

TOKEN_BYTES = 32


def mint_token(user_id: str, jwt_token: str) -> dict[str, Any]:
    """Generate a 256-bit URL-safe bearer token, persist it, return it.

    Returns ``{"token", "created_at", "expires_at"}``. ``expires_at`` is
    set to ``now() + connector_token_ttl_days``.
    """
    token = secrets.token_urlsafe(TOKEN_BYTES)
    expires_at = datetime.now(UTC) + timedelta(
        days=lib_settings.connector_token_ttl_days
    )
    res = (
        db.user_client(user_id, jwt_token)
        .table("connector_tokens")
        .insert(
            {
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at.isoformat(),
            }
        )
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    row = rows[0] if rows else {}
    return {
        "token": token,
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
    }


def lookup_token(token: str) -> str | None:
    """Resolve a bearer token to its user_id via the security-definer RPC.

    The RPC filters expired and revoked tokens — those collapse to NULL,
    same as an unknown token — and stamps ``last_used_at`` on a hit.
    Returns the user_id as ``str`` or ``None``.
    """
    res = db.anon_client().rpc("lookup_connector_token", {"p_token": token}).execute()
    user_id = res.data
    if not user_id:
        return None
    return str(user_id)


def list_tokens(user_id: str, jwt_token: str) -> list[dict[str, Any]]:
    """Return the caller's tokens (RLS scopes by user_id).

    Never returns the raw ``token`` value — only metadata for the
    settings page (id, created_at, last_used_at, expires_at, revoked_at).
    """
    res = (
        db.user_client(user_id, jwt_token)
        .table("connector_tokens")
        .select("id, created_at, last_used_at, expires_at, revoked_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def revoke_token(user_id: str, jwt_token: str, token_id: str) -> dict[str, Any]:
    """Set ``revoked_at = now()`` on the caller's token.

    RLS prevents revoking another user's token even if they guess the id;
    the defensive ``.eq("user_id", user_id)`` filter is belt-and-braces.
    Raises ``LookupError`` when no row matched (route layer maps to 404).
    """
    now = datetime.now(UTC).isoformat()
    res = (
        db.user_client(user_id, jwt_token)
        .table("connector_tokens")
        .update({"revoked_at": now})
        .eq("id", token_id)
        .eq("user_id", user_id)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        raise LookupError("token not found")
    return rows[0]
