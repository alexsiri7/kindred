"""Supabase REST-based token verification: valid, invalid, network error, missing bearer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth import get_current_user

USER_ID = "11111111-2222-3333-4444-555555555555"
TOKEN = "some-supabase-access-token"


def _bearer(token: str = TOKEN) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _mock_supabase_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


@pytest.mark.asyncio
async def test_valid_token_returns_user() -> None:
    mock_resp = _mock_supabase_response(200, {"id": USER_ID, "email": "u@example.com"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("auth.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        user = await get_current_user(_bearer())

    assert user["user_id"] == USER_ID
    assert user["email"] == "u@example.com"
    assert user["jwt"] == TOKEN


@pytest.mark.asyncio
async def test_get_current_user_returns_user_metadata() -> None:
    """user_metadata is surfaced so settings GET avoids a second admin round-trip."""
    metadata = {"timezone": "Europe/London", "transcript_enabled": False}
    mock_resp = _mock_supabase_response(
        200, {"id": USER_ID, "email": "u@example.com", "user_metadata": metadata}
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("auth.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        user = await get_current_user(_bearer())

    assert user["user_metadata"] == metadata


@pytest.mark.asyncio
async def test_get_current_user_user_metadata_defaults_to_empty_dict() -> None:
    mock_resp = _mock_supabase_response(200, {"id": USER_ID, "email": "u@example.com"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("auth.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        user = await get_current_user(_bearer())

    assert user["user_metadata"] == {}


@pytest.mark.asyncio
async def test_invalid_token_rejected() -> None:
    mock_resp = _mock_supabase_response(401, {"message": "Invalid JWT"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("auth.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_bearer("expired-or-bad-token"))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_network_error_raises_503() -> None:
    import httpx

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

    with patch("auth.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        with pytest.raises(HTTPException) as exc:
            await get_current_user(_bearer())

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_missing_bearer_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401
