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
from lib import db
from pydantic import BaseModel

from auth import get_current_user

router = APIRouter(tags=["settings"])


class SettingsPatch(BaseModel):
    timezone: str | None = None
    transcript_enabled: bool | None = None
    crisis_disclaimer_acknowledged_at: str | None = None


def _settings_response(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "timezone": meta.get("timezone"),
        "transcript_enabled": meta.get("transcript_enabled", True),
        "crisis_disclaimer_acknowledged_at": meta.get("crisis_disclaimer_acknowledged_at"),
    }


@router.get("/settings")
def get_settings(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    return _settings_response(cast(dict[str, Any], user.get("user_metadata") or {}))


@router.patch("/settings")
async def update_settings(
    patch: SettingsPatch,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    current = dict(cast(dict[str, Any], user.get("user_metadata") or {}))
    current.update(patch.model_dump(exclude_none=True))
    merged = await db.update_user_metadata(user["jwt"], current)
    return _settings_response(merged)


@router.get("/export")
def export_data(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    client = db.user_client(user["user_id"], user["jwt"])
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
    db.user_client(user["user_id"], user["jwt"]).rpc("delete_my_account").execute()
    return {"status": "deleted"}
