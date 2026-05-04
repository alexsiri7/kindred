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
