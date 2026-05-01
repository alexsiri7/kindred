"""GET /search?q=... — semantic search via match_entries RPC."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

import db
import embeddings
from auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str,
    limit: int = 5,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    if not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="query must not be empty"
        )
    vector = embeddings.embed(q)
    client = db.user_client(user["jwt"])
    res = client.rpc(
        "match_entries", {"query_embedding": vector, "match_count": limit}
    ).execute()
    raw: Any = res.data or []
    return list(raw)
