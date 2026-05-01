"""Tests for ConnectorTokenVerifier."""

from __future__ import annotations

from typing import Any

import pytest

import db
from auth import ConnectorTokenVerifier


@pytest.mark.asyncio
async def test_verify_token_unknown_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "lookup_connector_token", lambda _t: None)
    verifier = ConnectorTokenVerifier()
    assert await verifier.verify_token("does-not-exist") is None


@pytest.mark.asyncio
async def test_verify_token_known_returns_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = "11111111-2222-3333-4444-555555555555"

    def _fake_lookup(_t: str) -> dict[str, Any]:
        return {"user_id": user_id, "token": _t}

    monkeypatch.setattr(db, "lookup_connector_token", _fake_lookup)
    verifier = ConnectorTokenVerifier()
    token = await verifier.verify_token("good-token")
    assert token is not None
    assert token.client_id == user_id
    assert token.scopes == ["user"]
    assert token.expires_at is None
