"""Entry-related MCP tools: save, get, list_recent, search."""

from __future__ import annotations

import asyncio
from typing import Any

import db
import embeddings
from auth import current_user_id


async def save_entry(
    date: str,
    summary: str,
    mood: str | None = None,
    transcript: list[dict[str, str]] | None = None,
) -> str:
    """Persist a journaling session and embed its summary.

    Same-day re-entry: PRD §Open questions calls "append" the default but
    defers it as out of scope. Today's implementation creates a separate row
    per call — same-day callers will produce two rows.
    """
    user_id = current_user_id.get()
    entry_id = await asyncio.to_thread(
        db.insert_entry, user_id, date, summary, mood, transcript
    )
    vector = await asyncio.to_thread(embeddings.embed, summary)
    await asyncio.to_thread(db.insert_embedding, user_id, entry_id, vector, summary)
    return entry_id


async def get_entry(
    date: str | None = None,
    id: str | None = None,
) -> dict[str, Any]:
    if (date is None) == (id is None):
        raise ValueError("provide exactly one of `date` or `id`")
    user_id = current_user_id.get()
    if id is not None:
        row = await asyncio.to_thread(db.get_entry_by_id, user_id, id)
    else:
        assert date is not None
        row = await asyncio.to_thread(db.get_entry_by_date, user_id, date)
    if row is None:
        raise LookupError("entry not found")
    return row


async def list_recent_entries(limit: int = 10) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    return await asyncio.to_thread(db.list_recent_entries, user_id, limit)


async def search_entries(query: str, limit: int = 5) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    vector = await asyncio.to_thread(embeddings.embed, query)
    return await asyncio.to_thread(db.match_entries, user_id, vector, limit)
