"""GET /patterns, GET /patterns/:id — read-only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

import db
from auth import get_current_user

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("")
def list_patterns(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    client = db.user_client(user["jwt"])
    res = client.table("patterns").select("*").order("last_seen_at", desc=True).execute()
    raw: Any = res.data or []
    return list(raw)


@router.get("/{pattern_id}")
def get_pattern(
    pattern_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = db.user_client(user["jwt"])
    res = client.table("patterns").select("*").eq("id", pattern_id).limit(1).execute()
    raw: Any = res.data or []
    rows: list[dict[str, Any]] = list(raw)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pattern not found")
    pattern: dict[str, Any] = rows[0]
    occ_raw: Any = (
        client.table("pattern_occurrences")
        .select("*")
        .eq("pattern_id", pattern_id)
        .order("date", desc=True)
        .execute()
        .data
        or []
    )
    pattern["occurrences"] = list(occ_raw)
    return pattern
