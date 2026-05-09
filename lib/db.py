"""Supabase Client factory + every read/write helper used by services.

Two auth flows merged here:
- web flow: caller passes the user's Supabase JWT, we attach it directly.
- MCP flow: caller has only a user_id (resolved from a connector token);
  we mint a short-lived HS256 JWT signed with ``SUPABASE_JWT_SECRET`` per
  call. RLS still enforces ownership.

The defensive ``eq("user_id", user_id)`` filters on every query stay as
belt-and-braces — RLS protects against malicious clients, the filter
protects against bugs in our own code.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, cast
from uuid import UUID

import httpx
import jwt
from supabase import Client, create_client

from lib.settings import settings

_USER_JWT_TTL = timedelta(minutes=5)


def _supabase_user_jwt(user_id: str) -> str:
    """Mint a short-lived HS256 JWT PostgREST will accept as ``authenticated``.

    Both ``role`` and ``aud`` must equal ``"authenticated"`` or PostgREST
    rejects the request with a 401 — so callers see a clear failure rather
    than silently empty results. The TTL is short because we mint per call;
    do NOT cache across users.
    """
    if not settings.supabase_jwt_secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not configured")
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "aud": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + _USER_JWT_TTL).timestamp()),
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


@lru_cache(maxsize=1)
def _base_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def user_client(user_id: str, jwt_token: str | None = None) -> Client:
    """Anon-key client with a user JWT attached.

    If ``jwt_token`` is provided (web flow), it's attached as-is. If
    ``jwt_token`` is None (MCP flow), we mint one for ``user_id`` from
    ``SUPABASE_JWT_SECRET``. Either way RLS scopes every query.
    """
    client = _base_client()
    token = jwt_token if jwt_token is not None else _supabase_user_jwt(user_id)
    client.postgrest.auth(token)
    return client


@lru_cache(maxsize=1)
def anon_client() -> Client:
    """Anon-key client with no user JWT — only safe for security-definer RPCs."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def _table(user_id: str, jwt_token: str | None, name: str) -> Any:
    """Untyped query builder for a user-scoped client — typing escape hatch."""
    return user_client(user_id, jwt_token).table(name)


# ---------------------------------------------------------------------------
# entries
# ---------------------------------------------------------------------------
def insert_entry(
    user_id: str,
    jwt_token: str | None,
    date: str,
    summary: str,
    mood: str | None = None,
    transcript: list[dict[str, str]] | None = None,
) -> str:
    payload = {
        "user_id": user_id,
        "date": date,
        "summary": summary,
        "mood": mood,
        "transcript": transcript,
    }
    res = _table(user_id, jwt_token, "entries").insert(payload).execute()
    rows = res.data or []
    if not rows:
        raise RuntimeError("insert_entry returned no row")
    return str(rows[0]["id"])


def get_entry_by_id(
    user_id: str, jwt_token: str | None, entry_id: str
) -> dict[str, Any] | None:
    res = (
        _table(user_id, jwt_token, "entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("id", entry_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def get_entry_by_date(
    user_id: str, jwt_token: str | None, date: str
) -> dict[str, Any] | None:
    res = (
        _table(user_id, jwt_token, "entries")
        .select("*")
        .eq("user_id", user_id)
        .eq("date", date)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def list_recent_entries(
    user_id: str, jwt_token: str | None, limit: int = 10
) -> list[dict[str, Any]]:
    res = (
        _table(user_id, jwt_token, "entries")
        .select("id,date,summary,mood,created_at")
        .eq("user_id", user_id)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return list(res.data or [])


def delete_entry(user_id: str, jwt_token: str | None, entry_id: str) -> None:
    (
        _table(user_id, jwt_token, "entry_embeddings")
        .delete()
        .eq("user_id", user_id)
        .eq("entry_id", entry_id)
        .execute()
    )
    (
        _table(user_id, jwt_token, "entries")
        .delete()
        .eq("user_id", user_id)
        .eq("id", entry_id)
        .execute()
    )


# ---------------------------------------------------------------------------
# embeddings + semantic search
# ---------------------------------------------------------------------------
def insert_embedding(
    user_id: str,
    jwt_token: str | None,
    entry_id: str,
    embedding: list[float],
    content: str,
) -> None:
    _table(user_id, jwt_token, "entry_embeddings").insert(
        {
            "entry_id": entry_id,
            "user_id": user_id,
            "embedding": embedding,
            "content": content,
        }
    ).execute()


def match_entries(
    user_id: str,
    jwt_token: str | None,
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict[str, Any]]:
    res = (
        user_client(user_id, jwt_token)
        .rpc(
            "match_entries",
            {"query_embedding": query_embedding, "match_count": limit},
        )
        .execute()
    )
    raw: Any = res.data or []
    return list(raw)


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------
def find_pattern_by_name(
    user_id: str, jwt_token: str | None, name: str
) -> dict[str, Any] | None:
    # case-insensitive match; PostgREST `ilike` filter
    res = (
        _table(user_id, jwt_token, "patterns")
        .select("*")
        .eq("user_id", user_id)
        .ilike("name", name)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def list_patterns(
    user_id: str, jwt_token: str | None, active_since: str | None = None
) -> list[dict[str, Any]]:
    q = _table(user_id, jwt_token, "patterns").select("*").eq("user_id", user_id)
    if active_since is not None:
        q = q.gte("last_seen_at", active_since)
    res = q.order("last_seen_at", desc=True).execute()
    return list(res.data or [])


def get_pattern(
    user_id: str, jwt_token: str | None, name_or_id: str
) -> dict[str, Any] | None:
    try:
        UUID(name_or_id)
    except ValueError:
        return find_pattern_by_name(user_id, jwt_token, name_or_id)
    res = (
        _table(user_id, jwt_token, "patterns")
        .select("*")
        .eq("user_id", user_id)
        .eq("id", name_or_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def insert_pattern(
    user_id: str,
    jwt_token: str | None,
    name: str,
    typical_thoughts: str | None = None,
    typical_emotions: str | None = None,
    typical_behaviors: str | None = None,
    typical_sensations: str | None = None,
    description: str | None = None,
) -> str:
    payload = {
        "user_id": user_id,
        "name": name,
        "description": description,
        "typical_thoughts": typical_thoughts,
        "typical_emotions": typical_emotions,
        "typical_behaviors": typical_behaviors,
        "typical_sensations": typical_sensations,
    }
    res = _table(user_id, jwt_token, "patterns").insert(payload).execute()
    rows = res.data or []
    if not rows:
        raise RuntimeError("insert_pattern returned no row")
    return str(rows[0]["id"])


def update_pattern_seen(
    user_id: str,
    jwt_token: str | None,
    pattern_id: str,
    last_seen_at: str | None = None,
) -> None:
    last_seen = last_seen_at or datetime.now(UTC).isoformat()
    # Read-then-write because PostgREST doesn't support raw SQL increments.
    res = (
        _table(user_id, jwt_token, "patterns")
        .select("occurrence_count")
        .eq("id", pattern_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    current = int(rows[0]["occurrence_count"]) if rows else 0
    _table(user_id, jwt_token, "patterns").update(
        {"last_seen_at": last_seen, "occurrence_count": current + 1}
    ).eq("id", pattern_id).execute()


# ---------------------------------------------------------------------------
# pattern_occurrences
# ---------------------------------------------------------------------------
def insert_occurrence(
    user_id: str,
    jwt_token: str | None,
    pattern_id: str,
    entry_id: str,
    date: str,
    thoughts: str,
    emotions: str,
    behaviors: str,
    sensations: str,
    intensity: int | None = None,
    trigger: str | None = None,
    notes: str | None = None,
) -> str:
    payload = {
        "user_id": user_id,
        "pattern_id": pattern_id,
        "entry_id": entry_id,
        "date": date,
        "thoughts": thoughts,
        "emotions": emotions,
        "behaviors": behaviors,
        "sensations": sensations,
        "intensity": intensity,
        "trigger": trigger,
        "notes": notes,
    }
    res = _table(user_id, jwt_token, "pattern_occurrences").insert(payload).execute()
    rows = res.data or []
    if not rows:
        raise RuntimeError("insert_occurrence returned no row")
    return str(rows[0]["id"])


def list_occurrences(
    user_id: str,
    jwt_token: str | None,
    pattern_id: str,
    since: str | None = None,
) -> list[dict[str, Any]]:
    q = (
        _table(user_id, jwt_token, "pattern_occurrences")
        .select("*")
        .eq("user_id", user_id)
        .eq("pattern_id", pattern_id)
    )
    if since is not None:
        q = q.gte("date", since)
    res = q.order("date", desc=True).execute()
    return list(res.data or [])


def list_occurrences_for_entry(
    user_id: str, jwt_token: str | None, entry_id: str
) -> list[dict[str, Any]]:
    res = (
        _table(user_id, jwt_token, "pattern_occurrences")
        .select("*")
        .eq("user_id", user_id)
        .eq("entry_id", entry_id)
        .order("created_at", desc=True)
        .execute()
    )
    return list(res.data or [])


# ---------------------------------------------------------------------------
# auth.users metadata (GoTrue self-service)
# ---------------------------------------------------------------------------
async def update_user_metadata(
    jwt_token: str, metadata: dict[str, Any]
) -> dict[str, Any]:
    """Self-service metadata update via GoTrue's PUT /auth/v1/user.

    GoTrue's user-side endpoint expects ``{"data": {...}}`` (NOT
    ``{"user_metadata": {...}}``). Returns the merged ``user_metadata`` from
    the response so callers get the persisted state, not a local copy.
    """
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.put(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {jwt_token}",
            },
            json={"data": metadata},
        )
    resp.raise_for_status()
    data = resp.json()
    return cast(dict[str, Any], data.get("user_metadata") or {})


__all__ = [
    "anon_client",
    "delete_entry",
    "find_pattern_by_name",
    "get_entry_by_date",
    "get_entry_by_id",
    "get_pattern",
    "insert_embedding",
    "insert_entry",
    "insert_occurrence",
    "insert_pattern",
    "list_occurrences",
    "list_occurrences_for_entry",
    "list_patterns",
    "list_recent_entries",
    "match_entries",
    "update_pattern_seen",
    "update_user_metadata",
    "user_client",
]
