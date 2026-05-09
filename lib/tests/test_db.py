"""Tests for the per-request user JWT minted by ``db.user_client``.

Without these, an ``aud`` or ``role`` typo silently breaks RLS — PostgREST
returns empty data, not an error, and tools just go quiet.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest

from lib import db
from lib import settings as settings_module

JWT_SECRET = "test-jwt-secret-needs-to-be-at-least-32-bytes-long"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def _supabase_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "supabase_jwt_secret", JWT_SECRET)


def test_user_client_jwt_signed_with_supabase_jwt_secret(
    _supabase_jwt_secret: None,
) -> None:
    token = db._supabase_user_jwt(USER_ID)
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    assert payload["sub"] == USER_ID


def test_user_client_jwt_role_and_aud_are_authenticated(
    _supabase_jwt_secret: None,
) -> None:
    """Both claims must be ``authenticated`` or PostgREST 401s the request."""
    token = db._supabase_user_jwt(USER_ID)
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    assert payload["role"] == "authenticated"
    assert payload["aud"] == "authenticated"


def test_user_client_jwt_short_ttl(_supabase_jwt_secret: None) -> None:
    """5-minute TTL prevents long-lived JWT reuse across requests."""
    before = int(datetime.now(UTC).timestamp())
    token = db._supabase_user_jwt(USER_ID)
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    ttl = payload["exp"] - before
    assert 0 < ttl <= 5 * 60 + 5  # +5s tolerance for slow CI clocks


def test_user_client_raises_when_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "supabase_jwt_secret", "")
    with pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET"):
        db._supabase_user_jwt(USER_ID)


def test_user_client_attaches_jwt_via_postgrest_auth(
    _supabase_jwt_secret: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``user_client`` must call ``client.postgrest.auth(jwt)`` exactly once
    when called without an explicit JWT (MCP flow)."""
    fake_client = MagicMock()

    def _fake_create_client(_url: str, _key: str) -> Any:
        return fake_client

    db._base_client.cache_clear()
    monkeypatch.setattr(db, "create_client", _fake_create_client)
    db.user_client(USER_ID, None)
    db._base_client.cache_clear()
    fake_client.postgrest.auth.assert_called_once()
    (jwt_arg,), _ = fake_client.postgrest.auth.call_args
    payload = jwt.decode(jwt_arg, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    assert payload["sub"] == USER_ID


def test_user_client_passes_through_provided_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``user_client(uid, jwt)`` (web flow) attaches the caller-supplied JWT verbatim."""
    fake_client = MagicMock()

    def _fake_create_client(_url: str, _key: str) -> Any:
        return fake_client

    db._base_client.cache_clear()
    monkeypatch.setattr(db, "create_client", _fake_create_client)
    db.user_client(USER_ID, "caller-supplied-jwt")
    db._base_client.cache_clear()
    fake_client.postgrest.auth.assert_called_once_with("caller-supplied-jwt")
