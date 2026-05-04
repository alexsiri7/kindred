"""GET /entries, GET /entries/:id — read-only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from lib.services import entries as entries_service

from auth import get_current_user

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("")
def list_entries(
    limit: int = 20,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return entries_service.list_recent_entries(
        user["user_id"], user["jwt"], limit=limit
    )


@router.get("/{entry_id}")
def get_entry(
    entry_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return entries_service.get_entry_with_occurrences(
            user["user_id"], user["jwt"], entry_id
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="entry not found"
        ) from None
