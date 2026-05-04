"""Tests for the 8 MCP tools — patched lib.db + lib.embeddings."""

from __future__ import annotations

from typing import Any

import pytest
from lib import db, embeddings

from auth import current_user_id
from tools import entries as entry_tools
from tools import patterns as pattern_tools

USER_ID = "00000000-1111-2222-3333-444444444444"
ENTRY_ID = "55555555-6666-7777-8888-999999999999"
PATTERN_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OCCURRENCE_ID = "ffffffff-1111-2222-3333-444444444444"


@pytest.fixture(autouse=True)
def _set_user() -> Any:
    token = current_user_id.set(USER_ID)
    yield
    current_user_id.reset(token)


# ---------------------------------------------------------------------------
# entries
# ---------------------------------------------------------------------------
async def test_save_entry_inserts_then_embeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_insert_entry(
        user_id: str, jwt_token: str | None, *args: Any, **kw: Any
    ) -> str:
        assert user_id == USER_ID
        assert jwt_token is None
        calls.append("insert_entry")
        return ENTRY_ID

    def fake_embed(text: str) -> list[float]:
        assert text == "today was hard"
        calls.append("embed")
        return [0.1, 0.2, 0.3]

    def fake_insert_embedding(
        user_id: str,
        jwt_token: str | None,
        entry_id: str,
        vector: list[float],
        content: str,
    ) -> None:
        assert user_id == USER_ID
        assert entry_id == ENTRY_ID
        assert vector == [0.1, 0.2, 0.3]
        assert content == "today was hard"
        calls.append("insert_embedding")

    monkeypatch.setattr(db, "insert_entry", fake_insert_entry)
    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(db, "insert_embedding", fake_insert_embedding)

    result = await entry_tools.save_entry("2026-05-01", "today was hard")
    assert result == ENTRY_ID
    assert calls == ["insert_entry", "embed", "insert_embedding"]


async def test_get_entry_requires_exactly_one_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "get_entry_by_id", lambda u, j, i: {"id": i})
    with pytest.raises(ValueError):
        await entry_tools.get_entry()
    with pytest.raises(ValueError):
        await entry_tools.get_entry(date="2026-05-01", id=ENTRY_ID)


async def test_get_entry_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(user_id: str, jwt_token: str | None, entry_id: str) -> dict[str, Any]:
        assert user_id == USER_ID
        return {"id": entry_id, "summary": "hi"}

    monkeypatch.setattr(db, "get_entry_by_id", fake)
    result = await entry_tools.get_entry(id=ENTRY_ID)
    assert result["id"] == ENTRY_ID


async def test_list_recent_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(user_id: str, jwt_token: str | None, limit: int) -> list[dict[str, Any]]:
        assert user_id == USER_ID
        assert limit == 3
        return [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    monkeypatch.setattr(db, "list_recent_entries", fake)
    rows = await entry_tools.list_recent_entries(limit=3)
    assert len(rows) == 3


async def test_search_entries_embeds_then_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_embed(text: str) -> list[float]:
        seen["embed"] = text
        return [0.5] * 3

    def fake_match(
        user_id: str, jwt_token: str | None, vector: list[float], limit: int
    ) -> list[dict[str, Any]]:
        seen["match"] = (user_id, vector, limit)
        return [{"entry_id": ENTRY_ID, "similarity": 0.9, "content": "x"}]

    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(db, "match_entries", fake_match)
    rows = await entry_tools.search_entries("loneliness", limit=2)
    assert seen["embed"] == "loneliness"
    assert seen["match"] == (USER_ID, [0.5, 0.5, 0.5], 2)
    assert rows[0]["entry_id"] == ENTRY_ID


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------
async def test_log_occurrence_creates_pattern_when_missing(
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

    occ = await pattern_tools.log_occurrence(
        pattern_name="Sunday dread",
        entry_id=ENTRY_ID,
        thoughts="this week will be brutal",
        emotions="dread",
        behaviors="doomscrolling",
        sensations="tight chest",
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


async def test_log_occurrence_rejects_out_of_range_intensity() -> None:
    with pytest.raises(ValueError):
        await pattern_tools.log_occurrence(
            pattern_name="x",
            entry_id=ENTRY_ID,
            thoughts="t",
            emotions="e",
            behaviors="b",
            sensations="s",
            intensity=7,
        )


async def test_list_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(
        user_id: str, jwt_token: str | None, since: str | None
    ) -> list[dict[str, Any]]:
        assert user_id == USER_ID
        return [{"id": PATTERN_ID, "name": "Sunday dread"}]

    monkeypatch.setattr(db, "list_patterns", fake)
    rows = await pattern_tools.list_patterns()
    assert rows[0]["name"] == "Sunday dread"


async def test_get_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(user_id: str, jwt_token: str | None, name_or_id: str) -> dict[str, Any]:
        assert user_id == USER_ID
        return {"id": PATTERN_ID, "name": name_or_id}

    monkeypatch.setattr(db, "get_pattern", fake)
    row = await pattern_tools.get_pattern("Sunday dread")
    assert row["id"] == PATTERN_ID


async def test_list_occurrences(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_find(
        user_id: str, jwt_token: str | None, name: str
    ) -> dict[str, Any]:
        return {"id": PATTERN_ID, "name": name}

    def fake_list(
        user_id: str,
        jwt_token: str | None,
        pattern_id: str,
        since: str | None,
    ) -> list[dict[str, Any]]:
        assert user_id == USER_ID
        assert pattern_id == PATTERN_ID
        return [{"id": OCCURRENCE_ID}]

    monkeypatch.setattr(db, "find_pattern_by_name", fake_find)
    monkeypatch.setattr(db, "list_occurrences", fake_list)
    rows = await pattern_tools.list_occurrences("Sunday dread")
    assert rows[0]["id"] == OCCURRENCE_ID
