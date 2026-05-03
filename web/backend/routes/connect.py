"""POST /connect/token — mint a long-lived bearer token for the user's MCP client connector.

We don't expose a GET (the user pasted the value into their MCP client and won't
reuse a stale one) and don't expose DELETE yet (revocation is on the build
order but out of scope for v1, per PRD §Build order step 8).
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends

import db
from auth import get_current_user

router = APIRouter(prefix="/connect", tags=["connect"])

TOKEN_BYTES = 32


@router.post("/token")
def mint_token(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    res = (
        db.user_client(user["jwt"])
        .table("connector_tokens")
        .insert({"user_id": user["user_id"], "token": token})
        .execute()
    )
    raw: Any = res.data or []
    rows: list[dict[str, Any]] = list(raw)
    created_at = rows[0].get("created_at") if rows else None
    return {"token": token, "created_at": created_at}
