"""User-facing settings, data export, and account deletion.

Settings (timezone, transcript_enabled) live in ``auth.users.user_metadata``
to avoid a 5th application table for what is, today, two scalar fields.
GET reads ``user_metadata`` from the auth dependency (already fetched from
GoTrue); PATCH writes via the self-service ``PUT /auth/v1/user``; DELETE
calls the ``delete_my_account`` security-definer RPC.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import db
from auth import get_current_user

router = APIRouter(tags=["settings"])


def _user_metadata(user: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], user.get("user_metadata") or {})


class SettingsPatch(BaseModel):
    timezone: str | None = None
    transcript_enabled: bool | None = None
    crisis_disclaimer_acknowledged_at: str | None = None


@router.get("/settings")
def get_settings(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    meta = _user_metadata(user)
    return {
        "timezone": meta.get("timezone"),
        "transcript_enabled": meta.get("transcript_enabled", True),
        "crisis_disclaimer_acknowledged_at": meta.get(
            "crisis_disclaimer_acknowledged_at"
        ),
    }


@router.patch("/settings")
async def update_settings(
    patch: SettingsPatch,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    current = dict(_user_metadata(user))
    if patch.timezone is not None:
        current["timezone"] = patch.timezone
    if patch.transcript_enabled is not None:
        current["transcript_enabled"] = patch.transcript_enabled
    if patch.crisis_disclaimer_acknowledged_at is not None:
        current["crisis_disclaimer_acknowledged_at"] = (
            patch.crisis_disclaimer_acknowledged_at
        )
    merged = await db.update_user_metadata(user["jwt"], current)
    return {
        "timezone": merged.get("timezone"),
        "transcript_enabled": merged.get("transcript_enabled", True),
        "crisis_disclaimer_acknowledged_at": merged.get(
            "crisis_disclaimer_acknowledged_at"
        ),
    }


@router.get("/export")
def export_data(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = db.user_client(user["jwt"])
    entries = client.table("entries").select("*").execute()
    patterns = client.table("patterns").select("*").execute()
    occurrences = client.table("pattern_occurrences").select("*").execute()
    return {
        "user_id": user["user_id"],
        "entries": list(entries.data or []),
        "patterns": list(patterns.data or []),
        "pattern_occurrences": list(occurrences.data or []),
    }


@router.delete("/account")
def delete_account(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    # The security-definer RPC deletes auth.users for auth.uid(); FK ON
    # DELETE CASCADE on every user-owned table cleans up app data atomically.
    db.user_client(user["jwt"]).rpc("delete_my_account").execute()
    return {"status": "deleted"}
