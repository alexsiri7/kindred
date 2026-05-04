"""GET /search?q=... — semantic search via match_entries RPC."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from lib.services import entries as entries_service

from auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str,
    limit: int = 5,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return entries_service.search_entries(
            user["user_id"], user["jwt"], q, limit
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
