"""Tests for lib.services.entries — patched lib.db + lib.embeddings."""

from __future__ import annotations

from typing import Any

import pytest

from lib import db, embeddings
from lib.services import entries as entries_service

USER_ID = "00000000-1111-2222-3333-444444444444"
ENTRY_ID = "55555555-6666-7777-8888-999999999999"


def test_save_entry_inserts_then_embeds(monkeypatch: pytest.MonkeyPatch) -> None:
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

    result = entries_service.save_entry(USER_ID, None, "2026-05-01", "today was hard")
    assert result == ENTRY_ID
    assert calls == ["insert_entry", "embed", "insert_embedding"]


def test_search_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        entries_service.search_entries(USER_ID, None, "   ")


def test_get_entry_by_date_or_id_requires_exactly_one_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError):
        entries_service.get_entry_by_date_or_id(USER_ID, None)
    with pytest.raises(ValueError):
        entries_service.get_entry_by_date_or_id(
            USER_ID, None, date="2026-05-01", entry_id=ENTRY_ID
        )


def test_get_entry_with_occurrences_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "get_entry_by_id", lambda *a, **k: None)
    with pytest.raises(LookupError):
        entries_service.get_entry_with_occurrences(USER_ID, None, ENTRY_ID)


def test_get_entry_with_occurrences_attaches_occurrences_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The frontend timeline reads the ``occurrences`` key off the entry payload."""
    monkeypatch.setattr(
        db,
        "get_entry_by_id",
        lambda u, j, eid: {"id": eid, "date": "2026-05-01", "summary": "x"},
    )
    monkeypatch.setattr(
        db,
        "list_occurrences_for_entry",
        lambda u, j, eid: [{"id": "occ-1", "entry_id": eid}],
    )
    out = entries_service.get_entry_with_occurrences(USER_ID, None, ENTRY_ID)
    assert out["id"] == ENTRY_ID
    assert out["occurrences"] == [{"id": "occ-1", "entry_id": ENTRY_ID}]


def test_get_entry_by_date_or_id_dispatches_to_correct_db_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        db, "get_entry_by_id", lambda u, j, eid: {"id": eid, "via": "id"}
    )
    monkeypatch.setattr(
        db,
        "get_entry_by_date",
        lambda u, j, d: {"id": "x", "via": "date", "date": d},
    )
    by_id = entries_service.get_entry_by_date_or_id(
        USER_ID, None, entry_id=ENTRY_ID
    )
    by_date = entries_service.get_entry_by_date_or_id(
        USER_ID, None, date="2026-05-01"
    )
    assert by_id["via"] == "id"
    assert by_id["id"] == ENTRY_ID
    assert by_date["via"] == "date"
    assert by_date["date"] == "2026-05-01"


def test_search_entries_embeds_then_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate → embed → match: order and arg-shape pinned at service level."""
    captured: dict[str, Any] = {}

    def fake_embed(q: str) -> list[float]:
        captured["q"] = q
        return [0.1, 0.2]

    def fake_match(
        u: str, j: str | None, vec: list[float], limit: int
    ) -> list[dict[str, Any]]:
        captured["uid"] = u
        captured["jwt"] = j
        captured["vec"] = vec
        captured["limit"] = limit
        return [{"entry_id": "e1", "similarity": 0.9}]

    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(db, "match_entries", fake_match)
    out = entries_service.search_entries(USER_ID, "the-jwt", "loneliness", limit=3)
    assert captured == {
        "q": "loneliness",
        "uid": USER_ID,
        "jwt": "the-jwt",
        "vec": [0.1, 0.2],
        "limit": 3,
    }
    assert out[0]["entry_id"] == "e1"


def test_list_recent_entries_passes_through_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake(u: str, j: str | None, limit: int) -> list[dict[str, Any]]:
        captured.update(uid=u, jwt=j, limit=limit)
        return [{"id": "e1"}]

    monkeypatch.setattr(db, "list_recent_entries", fake)
    out = entries_service.list_recent_entries(USER_ID, "the-jwt", 7)
    assert out == [{"id": "e1"}]
    assert captured == {"uid": USER_ID, "jwt": "the-jwt", "limit": 7}


def test_save_entry_logs_when_embedding_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Embedding failure must surface a log line so the orphan entry is discoverable."""

    def fake_insert_entry(*a: Any, **k: Any) -> str:
        return ENTRY_ID

    def fake_embed(_: str) -> list[float]:
        raise RuntimeError("requesty 5xx")

    monkeypatch.setattr(db, "insert_entry", fake_insert_entry)
    monkeypatch.setattr(embeddings, "embed", fake_embed)
    with caplog.at_level("ERROR"), pytest.raises(RuntimeError, match="requesty 5xx"):
        entries_service.save_entry(USER_ID, None, "2026-05-01", "x")
    assert any(
        "persisted without embedding" in record.message for record in caplog.records
    )
