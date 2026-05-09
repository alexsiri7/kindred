"""Local HS256 token verification: valid, invalid, missing bearer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import settings as settings_module
from auth import get_current_user

JWT_SECRET = "test-jwt-secret-needs-to-be-at-least-32-bytes-long"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _patch_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "supabase_jwt_secret", JWT_SECRET)


def _make_token(
    sub: str = USER_ID,
    email: str = "u@example.com",
    user_metadata: dict | None = None,
    secret: str = JWT_SECRET,
    aud: str = "authenticated",
    exp_delta: timedelta = timedelta(minutes=5),
) -> str:
    now = datetime.now(UTC)
    claims: dict = {
        "sub": sub,
        "email": email,
        "aud": aud,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
    }
    if user_metadata is not None:
        claims["user_metadata"] = user_metadata
    return jwt.encode(claims, secret, algorithm="HS256")


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_valid_token_returns_user() -> None:
    token = _make_token()
    user = await get_current_user(_bearer(token))
    assert user["user_id"] == USER_ID
    assert user["email"] == "u@example.com"
    assert user["jwt"] == token


@pytest.mark.asyncio
async def test_get_current_user_returns_user_metadata() -> None:
    metadata = {"timezone": "Europe/London", "transcript_enabled": False}
    token = _make_token(user_metadata=metadata)
    user = await get_current_user(_bearer(token))
    assert user["user_metadata"] == metadata


@pytest.mark.asyncio
async def test_get_current_user_user_metadata_defaults_to_empty_dict() -> None:
    token = _make_token()
    user = await get_current_user(_bearer(token))
    assert user["user_metadata"] == {}


@pytest.mark.asyncio
async def test_invalid_token_rejected() -> None:
    token = _make_token(secret="wrong-secret-that-will-not-verify-at-all!")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_bearer(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_bearer_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401
