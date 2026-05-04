"""Tests for lib.services.tokens — patched lib.db."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from lib import db
from lib.services import tokens

USER_ID = "00000000-1111-2222-3333-444444444444"
TOKEN_ID = "aaaa1111-bbbb-2222-cccc-333333333333"


def test_mint_token_returns_url_safe_token(monkeypatch: pytest.MonkeyPatch) -> None:
    inserted: dict[str, Any] = {}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = [
            {
                "created_at": "2026-05-01T00:00:00Z",
                "expires_at": "2026-07-30T00:00:00Z",
            }
        ]

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
    assert out["expires_at"] == "2026-07-30T00:00:00Z"


def test_mint_token_writes_expires_at_around_ttl_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inserted: dict[str, Any] = {}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = []

        def _insert(payload: dict[str, Any]) -> MagicMock:
            inserted["payload"] = payload
            exec_mock = MagicMock()
            exec_mock.execute.return_value = response
            return exec_mock

        table.insert.side_effect = _insert
        sb.table.return_value = table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    before = datetime.now(UTC)
    tokens.mint_token(USER_ID, "fake-jwt")
    after = datetime.now(UTC)

    expires_at = datetime.fromisoformat(inserted["payload"]["expires_at"])
    # Default TTL is 90 days; allow ±1 day slack for clock noise.
    assert before + timedelta(days=89) <= expires_at <= after + timedelta(days=91)


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


def test_list_tokens_filters_by_user_and_returns_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "id": TOKEN_ID,
            "created_at": "2026-05-01T00:00:00Z",
            "last_used_at": None,
            "expires_at": "2026-07-30T00:00:00Z",
            "revoked_at": None,
        }
    ]
    chain_calls: dict[str, Any] = {}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = rows

        select = table.select.return_value
        eq = select.eq.return_value

        def _eq(field: str, value: Any) -> MagicMock:
            chain_calls["eq_field"] = field
            chain_calls["eq_value"] = value
            return eq

        select.eq.side_effect = _eq
        eq.order.return_value.execute.return_value = response
        sb.table.return_value = table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    out = tokens.list_tokens(USER_ID, "fake-jwt")
    assert out == rows
    assert chain_calls == {"eq_field": "user_id", "eq_value": USER_ID}


def test_revoke_token_updates_revoked_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    updated_row = {"id": TOKEN_ID, "revoked_at": "2026-05-04T12:00:00Z"}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = [updated_row]

        def _update(payload: dict[str, Any]) -> MagicMock:
            captured["payload"] = payload
            return update_chain

        update_chain = MagicMock()

        def _eq_id(field: str, value: Any) -> MagicMock:
            captured["eq_id_field"] = field
            captured["eq_id_value"] = value
            return eq_id_chain

        eq_id_chain = MagicMock()

        def _eq_user(field: str, value: Any) -> MagicMock:
            captured["eq_user_field"] = field
            captured["eq_user_value"] = value
            return eq_user_chain

        eq_user_chain = MagicMock()
        eq_user_chain.execute.return_value = response

        update_chain.eq.side_effect = _eq_id
        eq_id_chain.eq.side_effect = _eq_user

        table.update.side_effect = _update
        sb.table.return_value = table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    out = tokens.revoke_token(USER_ID, "fake-jwt", TOKEN_ID)
    assert out == updated_row
    assert "revoked_at" in captured["payload"]
    # ISO-format timestamp:
    datetime.fromisoformat(captured["payload"]["revoked_at"])
    assert captured["eq_id_field"] == "id"
    assert captured["eq_id_value"] == TOKEN_ID
    assert captured["eq_user_field"] == "user_id"
    assert captured["eq_user_value"] == USER_ID


def test_revoke_token_raises_when_no_row_updated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        table = MagicMock()
        response = MagicMock()
        response.data = []
        table.update.return_value.eq.return_value.eq.return_value.execute.return_value = (
            response
        )
        sb.table.return_value = table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    with pytest.raises(LookupError):
        tokens.revoke_token(USER_ID, "fake-jwt", TOKEN_ID)
