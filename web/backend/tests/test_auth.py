"""JWKS/ES256 token verification: valid, invalid, missing bearer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth import get_current_user

USER_ID = "11111111-2222-3333-4444-555555555555"

# Generate a throwaway EC P-256 key pair for tests.
_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


def _make_token(
    sub: str = USER_ID,
    email: str = "u@example.com",
    user_metadata: dict | None = None,
    private_key=_PRIVATE_KEY,
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
    return jwt.encode(claims, private_key, algorithm="ES256")


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _make_mock_jwks_client(public_key=_PUBLIC_KEY) -> MagicMock:
    """Return a mock PyJWKClient whose get_signing_key_from_jwt yields public_key.

    jwt.decode() accepts a raw EC public key object directly (the non-PyJWK path
    in api_jws._verify_signature), so we return the key itself — no wrapper needed.
    """
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = public_key
    return mock_client


@pytest.mark.asyncio
async def test_valid_token_returns_user() -> None:
    token = _make_token()
    with patch("auth._get_jwks_client", return_value=_make_mock_jwks_client()):
        user = await get_current_user(_bearer(token))
    assert user["user_id"] == USER_ID
    assert user["email"] == "u@example.com"
    assert user["jwt"] == token


@pytest.mark.asyncio
async def test_get_current_user_returns_user_metadata() -> None:
    metadata = {"timezone": "Europe/London", "transcript_enabled": False}
    token = _make_token(user_metadata=metadata)
    with patch("auth._get_jwks_client", return_value=_make_mock_jwks_client()):
        user = await get_current_user(_bearer(token))
    assert user["user_metadata"] == metadata


@pytest.mark.asyncio
async def test_get_current_user_user_metadata_defaults_to_empty_dict() -> None:
    token = _make_token()
    with patch("auth._get_jwks_client", return_value=_make_mock_jwks_client()):
        user = await get_current_user(_bearer(token))
    assert user["user_metadata"] == {}


@pytest.mark.asyncio
async def test_invalid_token_rejected() -> None:
    # Token signed with a different private key — wrong key, verification fails.
    other_private_key = ec.generate_private_key(ec.SECP256R1())
    token = _make_token(private_key=other_private_key)
    with patch("auth._get_jwks_client", return_value=_make_mock_jwks_client()):
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_bearer(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_bearer_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401
