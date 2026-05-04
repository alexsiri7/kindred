"""Tests for lib.services.tokens — patched lib.db."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lib import db
from lib.services import tokens

USER_ID = "00000000-1111-2222-3333-444444444444"


def test_mint_token_returns_url_safe_token(monkeypatch: pytest.MonkeyPatch) -> None:
    inserted: dict[str, Any] = {}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = [{"created_at": "2026-05-01T00:00:00Z"}]

        def _insert(payload: dict[str, Any]) -> MagicMock:
            inserted["payload"] = payload
            exec_mock = MagicMock()
            exec_mock.execute.return_value = response
            return exec_mock

        table.insert.side_effect = _insert
        sb.table.return_value = table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    out = tokens.mint_token(USER_ID, "fake-jwt")
    assert isinstance(out["token"], str)
    assert len(out["token"]) > 20
    assert inserted["payload"]["user_id"] == USER_ID
    assert out["created_at"] == "2026-05-01T00:00:00Z"


def test_lookup_token_returns_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_anon = MagicMock()
    fake_anon.rpc.return_value.execute.return_value = MagicMock(data=USER_ID)
    monkeypatch.setattr(db, "anon_client", lambda: fake_anon)
    assert tokens.lookup_token("any-token") == USER_ID


def test_lookup_token_returns_none_when_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_anon = MagicMock()
    fake_anon.rpc.return_value.execute.return_value = MagicMock(data=None)
    monkeypatch.setattr(db, "anon_client", lambda: fake_anon)
    assert tokens.lookup_token("nope") is None
