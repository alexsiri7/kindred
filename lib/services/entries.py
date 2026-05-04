"""Entry business logic: save, get, list, search.

Async/sync convention: these are sync. supabase-py 2.x is sync; the MCP
side wraps calls in ``asyncio.to_thread`` (see mcp/tools/entries.py); the
web side calls them directly from sync FastAPI routes.
"""

from __future__ import annotations

from typing import Any

from lib import db, embeddings


def save_entry(
    user_id: str,
    jwt_token: str | None,
    date: str,
    summary: str,
    mood: str | None = None,
    transcript: list[dict[str, str]] | None = None,
) -> str:
    """Persist a journaling session and embed its summary.

    Same-day re-entry creates a separate row per call (same as legacy
    behaviour — not a service-level concern).
    """
    entry_id = db.insert_entry(user_id, jwt_token, date, summary, mood, transcript)
    vector = embeddings.embed(summary)
    db.insert_embedding(user_id, jwt_token, entry_id, vector, summary)
    return entry_id


def get_entry_by_date_or_id(
    user_id: str,
    jwt_token: str | None,
    *,
    date: str | None = None,
    entry_id: str | None = None,
) -> dict[str, Any]:
    """Lookup a single entry by either ``date`` or ``entry_id`` (exactly one)."""
    if (date is None) == (entry_id is None):
        raise ValueError("provide exactly one of `date` or `entry_id`")
    if entry_id is not None:
        row = db.get_entry_by_id(user_id, jwt_token, entry_id)
    else:
        assert date is not None
        row = db.get_entry_by_date(user_id, jwt_token, date)
    if row is None:
        raise LookupError("entry not found")
    return row


def get_entry_with_occurrences(
    user_id: str, jwt_token: str | None, entry_id: str
) -> dict[str, Any]:
    """Single entry + its linked pattern_occurrences (web GET /entries/:id shape)."""
    entry = db.get_entry_by_id(user_id, jwt_token, entry_id)
    if entry is None:
        raise LookupError("entry not found")
    entry["occurrences"] = db.list_occurrences_for_entry(user_id, jwt_token, entry_id)
    return entry


def list_recent_entries(
    user_id: str, jwt_token: str | None, limit: int = 10
) -> list[dict[str, Any]]:
    return db.list_recent_entries(user_id, jwt_token, limit)


def search_entries(
    user_id: str,
    jwt_token: str | None,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    vector = embeddings.embed(query)
    return db.match_entries(user_id, jwt_token, vector, limit)
