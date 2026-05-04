"""Connector-token routes — mint, list, and revoke.

POST /connect/token              — mint a new bearer token (#41 lifecycle:
                                   carries an ``expires_at``).
GET  /connect/tokens             — list the caller's tokens (metadata only,
                                   never the raw value).
POST /connect/tokens/{id}/revoke — flag a token as revoked; the next MCP
                                   request using it gets 401.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from lib.services import tokens

from auth import get_current_user

router = APIRouter(prefix="/connect", tags=["connect"])


@router.post("/token")
def mint_token(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return tokens.mint_token(user["user_id"], user["jwt"])


@router.get("/tokens")
def list_tokens(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return tokens.list_tokens(user["user_id"], user["jwt"])


@router.post("/tokens/{token_id}/revoke")
def revoke_token(
    token_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return tokens.revoke_token(user["user_id"], user["jwt"], token_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="token not found"
        ) from exc
