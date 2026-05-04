"""Tests for lib.services.patterns — patched lib.db."""

from __future__ import annotations

from typing import Any

import pytest

from lib import db
from lib.services import patterns as patterns_service

USER_ID = "00000000-1111-2222-3333-444444444444"
ENTRY_ID = "55555555-6666-7777-8888-999999999999"
PATTERN_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OCCURRENCE_ID = "ffffffff-1111-2222-3333-444444444444"


def test_log_occurrence_rejects_out_of_range_intensity() -> None:
    with pytest.raises(ValueError):
        patterns_service.log_occurrence(
            USER_ID,
            None,
            "x",
            ENTRY_ID,
            "t",
            "e",
            "b",
            "s",
            intensity=7,
        )


def test_log_occurrence_creates_pattern_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inserted: dict[str, Any] = {}

    def fake_find(
        user_id: str, jwt_token: str | None, name: str
    ) -> dict[str, Any] | None:
        return None

    def fake_insert_pattern(
        user_id: str,
        jwt_token: str | None,
        name: str,
        t: str,
        e: str,
        b: str,
        s: str,
        *a: Any,
        **kw: Any,
    ) -> str:
        inserted["name"] = name
        inserted["typical"] = (t, e, b, s)
        return PATTERN_ID

    def fake_get_entry(
        user_id: str, jwt_token: str | None, entry_id: str
    ) -> dict[str, Any]:
        return {"id": entry_id, "date": "2026-05-01"}

    def fake_insert_occ(*args: Any, **kw: Any) -> str:
        return OCCURRENCE_ID

    def fake_update(
        user_id: str, jwt_token: str | None, *args: Any, **kw: Any
    ) -> None:
        assert user_id == USER_ID
        inserted["seen"] = True

    monkeypatch.setattr(db, "find_pattern_by_name", fake_find)
    monkeypatch.setattr(db, "insert_pattern", fake_insert_pattern)
    monkeypatch.setattr(db, "get_entry_by_id", fake_get_entry)
    monkeypatch.setattr(db, "insert_occurrence", fake_insert_occ)
    monkeypatch.setattr(db, "update_pattern_seen", fake_update)

    occ = patterns_service.log_occurrence(
        USER_ID,
        None,
        "Sunday dread",
        ENTRY_ID,
        "this week will be brutal",
        "dread",
        "doomscrolling",
        "tight chest",
    )
    assert occ == OCCURRENCE_ID
    assert inserted["name"] == "Sunday dread"
    assert inserted["typical"] == (
        "this week will be brutal",
        "dread",
        "doomscrolling",
        "tight chest",
    )
    assert inserted["seen"] is True


def test_get_pattern_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "get_pattern", lambda *a, **k: None)
    with pytest.raises(LookupError):
        patterns_service.get_pattern(USER_ID, None, "missing")
