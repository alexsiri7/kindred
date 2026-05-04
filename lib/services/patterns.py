"""Pattern business logic: list, get, log_occurrence, list_occurrences."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from lib import db


def list_patterns(
    user_id: str, jwt_token: str | None, active_since: str | None = None
) -> list[dict[str, Any]]:
    return db.list_patterns(user_id, jwt_token, active_since)


def get_pattern(
    user_id: str, jwt_token: str | None, name_or_id: str
) -> dict[str, Any]:
    row = db.get_pattern(user_id, jwt_token, name_or_id)
    if row is None:
        raise LookupError(f"pattern not found: {name_or_id}")
    return row


def get_pattern_with_occurrences(
    user_id: str, jwt_token: str | None, pattern_id: str
) -> dict[str, Any]:
    """Pattern + its occurrences (web GET /patterns/:id shape)."""
    row = db.get_pattern(user_id, jwt_token, pattern_id)
    if row is None:
        raise LookupError(f"pattern not found: {pattern_id}")
    row["occurrences"] = db.list_occurrences(user_id, jwt_token, pattern_id, since=None)
    return row


def log_occurrence(
    user_id: str,
    jwt_token: str | None,
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

    pattern = db.find_pattern_by_name(user_id, jwt_token, pattern_name)
    if pattern is None:
        # Auto-create using the occurrence's quadrants as the initial typical shape.
        pattern_id = db.insert_pattern(
            user_id,
            jwt_token,
            pattern_name,
            thoughts,
            emotions,
            behaviors,
            sensations,
        )
    else:
        pattern_id = str(pattern["id"])

    entry = db.get_entry_by_id(user_id, jwt_token, entry_id)
    if entry is None:
        raise LookupError(f"entry not found: {entry_id}")
    occurrence_date = str(entry["date"])

    occurrence_id = db.insert_occurrence(
        user_id,
        jwt_token,
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
    db.update_pattern_seen(user_id, jwt_token, pattern_id)
    return occurrence_id


def list_occurrences(
    user_id: str,
    jwt_token: str | None,
    pattern_name_or_id: str,
    since: str | None = None,
) -> list[dict[str, Any]]:
    try:
        UUID(pattern_name_or_id)
        pattern_id = pattern_name_or_id
    except ValueError:
        pattern = db.find_pattern_by_name(user_id, jwt_token, pattern_name_or_id)
        if pattern is None:
            raise LookupError(
                f"pattern not found: {pattern_name_or_id}"
            ) from None
        pattern_id = str(pattern["id"])
    return db.list_occurrences(user_id, jwt_token, pattern_id, since)
