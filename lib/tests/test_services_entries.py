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


def test_update_entry_patches_summary_and_reembeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_update_entry(
        user_id: str, jwt_token: str | None, entry_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        assert user_id == USER_ID
        assert entry_id == ENTRY_ID
        assert patch == {"summary": "new summary"}
        calls.append("update_entry")
        return {"id": ENTRY_ID, "summary": "new summary"}

    def fake_embed(text: str) -> list[float]:
        assert text == "new summary"
        calls.append("embed")
        return [0.1, 0.2, 0.3]

    def fake_update_embedding(
        user_id: str,
        jwt_token: str | None,
        entry_id: str,
        embedding: list[float],
        content: str,
    ) -> None:
        assert user_id == USER_ID
        assert entry_id == ENTRY_ID
        assert embedding == [0.1, 0.2, 0.3]
        assert content == "new summary"
        calls.append("update_embedding")

    monkeypatch.setattr(db, "update_entry", fake_update_entry)
    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(db, "update_embedding", fake_update_embedding)

    result = entries_service.update_entry(USER_ID, None, entry_id=ENTRY_ID, summary="new summary")
    assert result["id"] == ENTRY_ID
    assert calls == ["embed", "update_entry", "update_embedding"]


def test_update_entry_mood_only_no_reembed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_update_entry(
        user_id: str, jwt_token: str | None, entry_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        assert patch == {"mood": "calm"}
        calls.append("update_entry")
        return {"id": ENTRY_ID, "mood": "calm"}

    monkeypatch.setattr(db, "update_entry", fake_update_entry)

    result = entries_service.update_entry(USER_ID, None, entry_id=ENTRY_ID, mood="calm")
    assert result["id"] == ENTRY_ID
    assert calls == ["update_entry"]


def test_update_entry_raises_on_empty_patch() -> None:
    with pytest.raises(ValueError, match="at least one field"):
        entries_service.update_entry(USER_ID, None, entry_id=ENTRY_ID)


def test_update_entry_raises_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "update_entry", lambda *a, **k: None)
    with pytest.raises(LookupError):
        entries_service.update_entry(USER_ID, None, entry_id=ENTRY_ID, mood="sad")


def test_update_entry_requires_exactly_one_identifier() -> None:
    # Neither provided
    with pytest.raises(ValueError, match="exactly one"):
        entries_service.update_entry(USER_ID, None, mood="calm")

    # Both provided
    with pytest.raises(ValueError, match="exactly one"):
        entries_service.update_entry(
            USER_ID, None, date="2026-05-01", entry_id=ENTRY_ID, mood="calm"
        )


def test_update_entry_by_date_resolves_and_patches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: caller supplies date instead of entry_id."""
    calls: list[str] = []

    def fake_get_entry_by_date(
        user_id: str, jwt_token: str | None, date: str
    ) -> dict[str, Any]:
        assert user_id == USER_ID
        assert date == "2026-05-01"
        calls.append("get_entry_by_date")
        return {"id": ENTRY_ID, "summary": "old"}

    def fake_update_entry(
        user_id: str, jwt_token: str | None, entry_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        assert entry_id == ENTRY_ID
        assert patch == {"mood": "calm"}
        calls.append("update_entry")
        return {"id": ENTRY_ID, "mood": "calm"}

    monkeypatch.setattr(db, "get_entry_by_date", fake_get_entry_by_date)
    monkeypatch.setattr(db, "update_entry", fake_update_entry)

    result = entries_service.update_entry(USER_ID, None, date="2026-05-01", mood="calm")
    assert result["id"] == ENTRY_ID
    assert calls == ["get_entry_by_date", "update_entry"]


def test_update_entry_by_date_raises_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Date does not match any entry → LookupError."""
    monkeypatch.setattr(db, "get_entry_by_date", lambda *a, **k: None)

    with pytest.raises(LookupError, match="entry not found"):
        entries_service.update_entry(USER_ID, None, date="2099-01-01", mood="sad")


def test_update_entry_transcript_only_no_reembed(monkeypatch: pytest.MonkeyPatch) -> None:
    transcript = [{"role": "user", "content": "Hello"}]

    def fake_update_entry(
        user_id: str, jwt_token: str | None, entry_id: str, patch: dict[str, Any]
    ) -> dict[str, Any]:
        assert patch == {"transcript": transcript}
        return {"id": ENTRY_ID, "transcript": transcript}

    monkeypatch.setattr(db, "update_entry", fake_update_entry)

    result = entries_service.update_entry(USER_ID, None, entry_id=ENTRY_ID, transcript=transcript)
    assert result["id"] == ENTRY_ID


def test_get_entry_with_occurrences_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "get_entry_by_id", lambda *a, **k: None)
    with pytest.raises(LookupError):
        entries_service.get_entry_with_occurrences(USER_ID, None, ENTRY_ID)
