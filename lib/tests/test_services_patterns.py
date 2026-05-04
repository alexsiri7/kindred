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


def test_log_occurrence_uses_existing_pattern_when_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Steady-state path: pattern already exists, must NOT auto-create."""
    inserted: dict[str, Any] = {}

    monkeypatch.setattr(
        db,
        "find_pattern_by_name",
        lambda u, j, n: {"id": PATTERN_ID, "name": n},
    )
    monkeypatch.setattr(
        db,
        "insert_pattern",
        lambda *a, **k: pytest.fail(
            "must not auto-create when pattern exists"
        ),
    )
    monkeypatch.setattr(
        db,
        "get_entry_by_id",
        lambda u, j, eid: {"id": eid, "date": "2026-05-01"},
    )

    def fake_insert_occ(
        user_id: str,
        jwt_token: str | None,
        pattern_id: str,
        *a: Any,
        **k: Any,
    ) -> str:
        inserted["pattern_id"] = pattern_id
        return OCCURRENCE_ID

    monkeypatch.setattr(db, "insert_occurrence", fake_insert_occ)
    monkeypatch.setattr(db, "update_pattern_seen", lambda *a, **k: None)

    occ = patterns_service.log_occurrence(
        USER_ID, None, "Sunday dread", ENTRY_ID, "t", "e", "b", "s"
    )
    assert occ == OCCURRENCE_ID
    assert inserted["pattern_id"] == PATTERN_ID


def test_log_occurrence_raises_when_entry_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stale entry_id must raise LookupError, not produce a half-written row."""
    monkeypatch.setattr(
        db, "find_pattern_by_name", lambda *a, **k: {"id": PATTERN_ID}
    )
    monkeypatch.setattr(db, "get_entry_by_id", lambda *a, **k: None)
    with pytest.raises(LookupError, match="entry not found"):
        patterns_service.log_occurrence(
            USER_ID, None, "x", ENTRY_ID, "t", "e", "b", "s"
        )


def test_log_occurrence_validates_entry_before_creating_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bad entry_id + missing pattern: pattern must NOT be auto-created
    (no orphan in catalog on retry)."""
    monkeypatch.setattr(db, "find_pattern_by_name", lambda *a, **k: None)
    monkeypatch.setattr(
        db,
        "insert_pattern",
        lambda *a, **k: pytest.fail(
            "must not auto-create pattern when entry is missing"
        ),
    )
    monkeypatch.setattr(db, "get_entry_by_id", lambda *a, **k: None)
    with pytest.raises(LookupError, match="entry not found"):
        patterns_service.log_occurrence(
            USER_ID, None, "ghost", ENTRY_ID, "t", "e", "b", "s"
        )


def test_get_pattern_with_occurrences_attaches_occurrences_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        db,
        "get_pattern",
        lambda u, j, pid: {"id": pid, "name": "Sunday dread"},
    )
    monkeypatch.setattr(
        db,
        "list_occurrences",
        lambda u, j, pid, since: [{"id": "occ-1", "pattern_id": pid}],
    )
    out = patterns_service.get_pattern_with_occurrences(
        USER_ID, None, PATTERN_ID
    )
    assert out["name"] == "Sunday dread"
    assert out["occurrences"] == [{"id": "occ-1", "pattern_id": PATTERN_ID}]


def test_get_pattern_with_occurrences_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "get_pattern", lambda *a, **k: None)
    with pytest.raises(LookupError):
        patterns_service.get_pattern_with_occurrences(
            USER_ID, None, PATTERN_ID
        )


def test_list_occurrences_uses_uuid_directly_when_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        db,
        "find_pattern_by_name",
        lambda *a, **k: pytest.fail(
            "should not look up when arg is already a UUID"
        ),
    )
    captured: dict[str, Any] = {}

    def fake_list(
        u: str, j: str | None, pid: str, since: str | None
    ) -> list[dict[str, Any]]:
        captured["pid"] = pid
        return []

    monkeypatch.setattr(db, "list_occurrences", fake_list)
    patterns_service.list_occurrences(USER_ID, None, PATTERN_ID)
    assert captured["pid"] == PATTERN_ID


def test_list_occurrences_resolves_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        db,
        "find_pattern_by_name",
        lambda u, j, n: {"id": PATTERN_ID, "name": n},
    )
    monkeypatch.setattr(
        db, "list_occurrences", lambda *a, **k: [{"id": "o1"}]
    )
    out = patterns_service.list_occurrences(USER_ID, None, "Sunday dread")
    assert out == [{"id": "o1"}]


def test_list_occurrences_raises_when_name_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "find_pattern_by_name", lambda *a, **k: None)
    with pytest.raises(LookupError, match="pattern not found"):
        patterns_service.list_occurrences(USER_ID, None, "ghost")
