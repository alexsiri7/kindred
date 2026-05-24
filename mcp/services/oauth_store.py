"""Persistence layer for MCP OAuth 2.1 token stores (issue #125).

Wraps the two long-lived in-memory dicts in oauth_state:
  - refresh_tokens (30-day TTL): written on every token issuance/refresh,
    deleted on consumption, loaded at startup.
  - registered_clients (no TTL): written on /oauth/register, never deleted,
    loaded at startup.

Uses the Supabase service-role client (SUPABASE_SERVICE_ROLE_KEY) because tokens
are server-managed — they don't belong to any individual user row.
All reads/writes are synchronous (called from sync FastAPI handlers).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from lib.settings import settings as lib_settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_service_client: Client | None = None


def _client() -> Client:
    global _service_client
    if _service_client is None:
        from settings import settings as mcp_settings  # noqa: PLC0415

        _service_client = create_client(
            lib_settings.supabase_url,
            lib_settings.supabase_anon_key,
        )
        # Use service-role key to bypass RLS for server-internal tables
        _service_client.postgrest.auth(mcp_settings.supabase_service_role_key)
    return _service_client


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
        _client().table("oauth_refresh_tokens").upsert({
            "token": token,
            "user_id": entry["user_id"],
            "email": entry.get("email"),
            "client_id": entry["client_id"],
            "scope": entry.get("scope", "mcp"),
            "expires_at": expires_at,
            "access_token_issued_at": issued_at,
        }).execute()
    except Exception:
        logger.exception(
            "oauth_store: failed to persist refresh token for user %s", entry.get("user_id")
        )


def delete_refresh_token(token: str) -> None:
    """Delete a refresh token on consumption (rotation) or expiry."""
    try:
        _client().table("oauth_refresh_tokens").delete().eq("token", token).execute()
    except Exception:
        logger.exception("oauth_store: failed to delete refresh token %s", token[:8])


def load_refresh_tokens() -> dict[str, dict[str, Any]]:
    """Load all non-expired refresh tokens from DB. Called at startup."""
    try:
        now = datetime.now(UTC).isoformat()
        res = (
            _client()
            .table("oauth_refresh_tokens")
            .select("*")
            .gt("expires_at", now)
            .execute()
        )
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
    try:
        _client().table("oauth_registered_clients").upsert({
            "client_id": client_id,
            "client_secret": entry["client_secret"],
            "redirect_uris": entry.get("redirect_uris", []),
            "client_name": entry.get("client_name", ""),
            "grant_types": entry.get("grant_types", ["authorization_code"]),
            "response_types": entry.get("response_types", ["code"]),
            "token_endpoint_auth_method": entry.get(
                "token_endpoint_auth_method", "client_secret_post"
            ),
            "scope": entry.get("scope", "mcp"),
        }).execute()
    except Exception:
        logger.exception("oauth_store: failed to persist registered client %s", client_id)


def load_registered_clients() -> dict[str, dict[str, Any]]:
    """Load all registered clients from DB. Called at startup."""
    try:
        res = _client().table("oauth_registered_clients").select("*").execute()
        rows = cast(list[dict[str, Any]], res.data or [])
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            client_id = row.pop("client_id")
            result[client_id] = {**row, "client_id": client_id}
        logger.info("oauth_store: loaded %d registered client(s) from DB", len(result))
        return result
    except Exception:
        logger.exception(
            "oauth_store: failed to load registered clients; starting with empty store"
        )
        return {}
