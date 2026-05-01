"""Pattern-related MCP tools: list, get, log_occurrence, list_occurrences."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import db
from auth import current_user_id


async def list_patterns(active_since: str | None = None) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    rows = await asyncio.to_thread(db.list_patterns, user_id, active_since)
    return rows


async def get_pattern(name_or_id: str) -> dict[str, Any]:
    user_id = current_user_id.get()
    row = await asyncio.to_thread(db.get_pattern, user_id, name_or_id)
    if row is None:
        raise LookupError(f"pattern not found: {name_or_id}")
    return row


async def log_occurrence(
    pattern_name: str,
    entry_id: str,
    thoughts: str,
    emotions: str,
    behaviors: str,
    sensations: str,
    intensity: int | None = None,
    trigger: str | None = None,
    notes: str | None = None,
) -> str:
    if intensity is not None and not (1 <= intensity <= 5):
        raise ValueError("intensity must be between 1 and 5")
    user_id = current_user_id.get()

    pattern = await asyncio.to_thread(db.find_pattern_by_name, user_id, pattern_name)
    if pattern is None:
        # Auto-create using the occurrence's quadrants as the initial typical shape.
        pattern_id = await asyncio.to_thread(
            db.insert_pattern,
            user_id,
            pattern_name,
            thoughts,
            emotions,
            behaviors,
            sensations,
        )
    else:
        pattern_id = str(pattern["id"])

    entry = await asyncio.to_thread(db.get_entry_by_id, user_id, entry_id)
    if entry is None:
        raise LookupError(f"entry not found: {entry_id}")
    occurrence_date = str(entry["date"])

    occurrence_id = await asyncio.to_thread(
        db.insert_occurrence,
        user_id,
        pattern_id,
        entry_id,
        occurrence_date,
        thoughts,
        emotions,
        behaviors,
        sensations,
        intensity,
        trigger,
        notes,
    )
    await asyncio.to_thread(db.update_pattern_seen, pattern_id)
    return occurrence_id


async def list_occurrences(
    pattern_name_or_id: str, since: str | None = None
) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    try:
        UUID(pattern_name_or_id)
        pattern_id = pattern_name_or_id
    except ValueError:
        pattern = await asyncio.to_thread(db.find_pattern_by_name, user_id, pattern_name_or_id)
        if pattern is None:
            raise LookupError(f"pattern not found: {pattern_name_or_id}") from None
        pattern_id = str(pattern["id"])
    return await asyncio.to_thread(db.list_occurrences, user_id, pattern_id, since)
