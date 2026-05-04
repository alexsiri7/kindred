"""Connector-token lifecycle.

Tokens are minted by the web app's ``POST /connect/token`` endpoint and
looked up by the MCP server's auth middleware. Rotation and revocation
are deferred (PRD §Build order step 8).
"""

from __future__ import annotations

import secrets
from typing import Any

from lib import db

TOKEN_BYTES = 32


def mint_token(user_id: str, jwt_token: str) -> dict[str, Any]:
    """Generate a 256-bit URL-safe bearer token, persist it, return it.

    Returns ``{"token", "created_at"}`` matching the legacy route response
    so ``web/backend/routes/connect.py`` doesn't need a shape change.
    """
    token = secrets.token_urlsafe(TOKEN_BYTES)
    res = (
        db.user_client(user_id, jwt_token)
        .table("connector_tokens")
        .insert({"user_id": user_id, "token": token})
        .execute()
    )
    raw: Any = res.data or []
    rows: list[dict[str, Any]] = list(raw)
    if not rows:
        raise RuntimeError("mint_token returned no row")
    return {"token": token, "created_at": rows[0].get("created_at")}


def lookup_token(token: str) -> str | None:
    """Resolve a bearer token to its user_id via the security-definer RPC.

    The RPC returns the matching user_id (uuid) directly, or NULL when the
    token is unknown. Returns the user_id as ``str`` or ``None``.
    """
    res = db.anon_client().rpc("lookup_connector_token", {"p_token": token}).execute()
    user_id = res.data
    if user_id is None:
        return None
    return str(user_id)
