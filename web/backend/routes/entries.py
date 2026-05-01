"""GET /entries, GET /entries/:id — read-only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

import db
from auth import get_current_user

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("")
def list_entries(
    limit: int = 20,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    client = db.user_client(user["jwt"])
    res = (
        client.table("entries")
        .select("id,date,summary,mood,created_at")
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    raw: Any = res.data or []
    rows: list[dict[str, Any]] = list(raw)
    return rows


@router.get("/{entry_id}")
def get_entry(
    entry_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = db.user_client(user["jwt"])
    res = client.table("entries").select("*").eq("id", entry_id).limit(1).execute()
    raw: Any = res.data or []
    rows: list[dict[str, Any]] = list(raw)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entry not found")
    entry: dict[str, Any] = rows[0]
    occ_raw: Any = (
        client.table("pattern_occurrences")
        .select("*")
        .eq("entry_id", entry_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    entry["occurrences"] = list(occ_raw)
    return entry
