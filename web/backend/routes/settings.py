"""User-facing settings, data export, and account deletion.

Settings (timezone, transcript_enabled) live in ``auth.users.user_metadata``
to avoid a 5th application table for what is, today, two scalar fields.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import db
from auth import get_current_user

router = APIRouter(tags=["settings"])


class SettingsPatch(BaseModel):
    timezone: str | None = None
    transcript_enabled: bool | None = None
    crisis_disclaimer_acknowledged_at: str | None = None


def _user_metadata(user_id: str) -> dict[str, Any]:
    res = db.service_client().auth.admin.get_user_by_id(user_id)
    if res is None or res.user is None:
        return {}
    meta = getattr(res.user, "user_metadata", None) or {}
    return cast(dict[str, Any], meta)


@router.get("/settings")
def get_settings(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    meta = _user_metadata(user["user_id"])
    return {
        "timezone": meta.get("timezone"),
        "transcript_enabled": meta.get("transcript_enabled", True),
        "crisis_disclaimer_acknowledged_at": meta.get(
            "crisis_disclaimer_acknowledged_at"
        ),
    }


@router.patch("/settings")
def update_settings(
    patch: SettingsPatch,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    current = _user_metadata(user["user_id"])
    if patch.timezone is not None:
        current["timezone"] = patch.timezone
    if patch.transcript_enabled is not None:
        current["transcript_enabled"] = patch.transcript_enabled
    if patch.crisis_disclaimer_acknowledged_at is not None:
        current["crisis_disclaimer_acknowledged_at"] = (
            patch.crisis_disclaimer_acknowledged_at
        )
    db.service_client().auth.admin.update_user_by_id(
        user["user_id"], {"user_metadata": current}
    )
    return {
        "timezone": current.get("timezone"),
        "transcript_enabled": current.get("transcript_enabled", True),
        "crisis_disclaimer_acknowledged_at": current.get(
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
    # FK ON DELETE CASCADE on every user-owned table means the auth.users
    # delete cleans up app data too.
    db.service_client().auth.admin.delete_user(user["user_id"])
    return {"status": "deleted"}
