"""GET /patterns, GET /patterns/:id — read-only."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from lib.services import patterns as patterns_service

from auth import get_current_user

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("")
def list_patterns(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return patterns_service.list_patterns(user["user_id"], user["jwt"])


@router.get("/{pattern_id}")
def get_pattern(
    pattern_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return patterns_service.get_pattern_with_occurrences(
            user["user_id"], user["jwt"], pattern_id
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pattern not found"
        ) from None
