"""Persistence layer for MCP OAuth 2.1 token stores (issue #125).

Wraps the two long-lived in-memory dicts in oauth_state:
  - refresh_tokens (30-day TTL): written on every token issuance/refresh,
    deleted on consumption, loaded at startup.
  - registered_clients (no TTL): written on /oauth/register, never deleted,
    loaded at startup.

Uses security-definer RPC functions (005_oauth_token_rpcs.sql) callable via
the anon key — no service-role key required in request-handling code (#44).
All reads/writes are synchronous blocking calls (called from async FastAPI handlers).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, cast

from lib.db import anon_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------


def save_refresh_token(token: str, entry: dict[str, Any]) -> None:
    """Upsert a refresh token record. Called after every token issuance."""
    expires_at = entry["expires_at"]
    if isinstance(expires_at, datetime):
        expires_at = expires_at.isoformat()
    issued_at = entry.get("access_token_issued_at")
    if isinstance(issued_at, datetime):
        issued_at = issued_at.isoformat()
    try:
        anon_client().rpc(
            "upsert_oauth_refresh_token",
            {
                "p_token": token,
                "p_user_id": entry["user_id"],
                "p_email": entry.get("email"),
                "p_client_id": entry["client_id"],
                "p_scope": entry.get("scope", "mcp"),
                "p_expires_at": expires_at,
                "p_access_token_issued_at": issued_at,
            },
        ).execute()
    except Exception:
        logger.exception(
            "oauth_store: failed to persist refresh token for user %s", entry.get("user_id")
        )


def delete_refresh_token(token: str) -> None:
    """Delete a refresh token on consumption (token rotation).

    Note: expired tokens are not deleted here — they are filtered at load time
    by ``load_refresh_tokens`` (``expires_at > now``). Dead rows accumulate
    until a manual or scheduled cleanup runs.
    """
    try:
        anon_client().rpc("delete_oauth_refresh_token", {"p_token": token}).execute()
    except Exception:
        logger.exception(
            "oauth_store: failed to delete refresh token %s — "
            "token may be replayable after restart; consider manual cleanup",
            token[:8],
        )


def load_refresh_tokens() -> dict[str, dict[str, Any]]:
    """Load all non-expired refresh tokens from DB. Called at startup."""
    try:
        res = anon_client().rpc("load_oauth_refresh_tokens", {}).execute()
        rows = cast(list[dict[str, Any]], res.data or [])
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            token = row.pop("token")
            # Re-parse datetime strings to datetime objects to match in-memory format
            for field in ("expires_at", "access_token_issued_at", "created_at"):
                val = row.get(field)
                if val and isinstance(val, str):
                    try:
                        row[field] = datetime.fromisoformat(val)
                    except ValueError:
                        pass
            result[token] = row
        logger.info("oauth_store: loaded %d refresh token(s) from DB", len(result))
        return result
    except Exception:
        logger.exception("oauth_store: failed to load refresh tokens; starting with empty store")
        return {}


# ---------------------------------------------------------------------------
# registered_clients
# ---------------------------------------------------------------------------


def save_registered_client(client_id: str, entry: dict[str, Any]) -> None:
    """Upsert a registered client record. Called on /oauth/register."""
    redirect_uris = entry.get("redirect_uris", [])
    grant_types = entry.get("grant_types", ["authorization_code"])
    response_types = entry.get("response_types", ["code"])
    try:
        anon_client().rpc(
            "upsert_oauth_registered_client",
            {
                "p_client_id": client_id,
                "p_client_secret": entry["client_secret"],
                "p_redirect_uris": json.dumps(redirect_uris),
                "p_client_name": entry.get("client_name", ""),
                "p_grant_types": json.dumps(grant_types),
                "p_response_types": json.dumps(response_types),
                "p_token_endpoint_auth_method": entry.get(
                    "token_endpoint_auth_method", "client_secret_post"
                ),
                "p_scope": entry.get("scope", "mcp"),
            },
        ).execute()
    except Exception:
        logger.exception("oauth_store: failed to persist registered client %s", client_id)


def load_registered_clients() -> dict[str, dict[str, Any]]:
    """Load all registered clients from DB. Called at startup."""
    try:
        res = anon_client().rpc("load_oauth_registered_clients", {}).execute()
        rows = cast(list[dict[str, Any]], res.data or [])
        result = {row["client_id"]: row for row in rows}
        logger.info("oauth_store: loaded %d registered client(s) from DB", len(result))
        return result
    except Exception:
        logger.exception(
            "oauth_store: failed to load registered clients; starting with empty store"
        )
        return {}
