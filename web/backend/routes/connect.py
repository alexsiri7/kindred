"""POST /connect/token — mint a long-lived bearer token for the user's MCP client connector.

We don't expose a GET (the user pasted the value into their MCP client and won't
reuse a stale one) and don't expose DELETE yet (revocation is on the build
order but out of scope for v1, per PRD §Build order step 8).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from lib.services import tokens

from auth import get_current_user

router = APIRouter(prefix="/connect", tags=["connect"])


@router.post("/token")
def mint_token(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return tokens.mint_token(user["user_id"], user["jwt"])
