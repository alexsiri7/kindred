"""Supabase JWT dependency: valid, expired, wrong audience, missing bearer."""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth import get_current_user
from settings import settings

SECRET = "test-secret-please-rotate-32-bytes-or-more"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwt_secret", SECRET)


def _encode(claims: dict[str, object]) -> str:
    return jwt.encode(claims, SECRET, algorithm="HS256")


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_valid_token_returns_user() -> None:
    token = _encode(
        {
            "sub": USER_ID,
            "email": "u@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 60,
        }
    )
    user = get_current_user(_bearer(token))
    assert user["user_id"] == USER_ID
    assert user["email"] == "u@example.com"
    assert user["jwt"] == token


def test_expired_token_rejected() -> None:
    token = _encode(
        {"sub": USER_ID, "aud": "authenticated", "exp": int(time.time()) - 60}
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(_bearer(token))
    assert exc.value.status_code == 401


def test_wrong_audience_rejected() -> None:
    token = _encode(
        {"sub": USER_ID, "aud": "service_role", "exp": int(time.time()) + 60}
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(_bearer(token))
    assert exc.value.status_code == 401


def test_missing_bearer_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_user(None)
    assert exc.value.status_code == 401
