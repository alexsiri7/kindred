"""Unit tests for ``web/backend/db`` GoTrue self-service helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import db


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


@contextmanager
def _patched_async_client(resp: MagicMock) -> Iterator[None]:
    mock_http = AsyncMock()
    mock_http.put = AsyncMock(return_value=resp)
    with patch("db.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield


@pytest.mark.asyncio
async def test_update_user_metadata_returns_metadata_on_success() -> None:
    metadata = {"timezone": "Europe/London", "transcript_enabled": False}
    with _patched_async_client(_mock_response(200, {"user_metadata": metadata})):
        result = await db.update_user_metadata("fake-jwt", metadata)
    assert result == metadata


@pytest.mark.asyncio
async def test_update_user_metadata_401_translates_to_http_exception() -> None:
    """Expired JWT (401) must surface as 401 HTTPException, not opaque 500."""
    with _patched_async_client(_mock_response(401, {"message": "Invalid JWT"})):
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("expired-jwt", {"timezone": "UTC"})
    assert exc.value.status_code == 401
    assert "Re-authentication" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_metadata_422_translates_to_http_exception() -> None:
    """Malformed metadata (422) must surface as 422 HTTPException, not opaque 500."""
    with _patched_async_client(_mock_response(422, {"message": "bad payload"})):
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("fake-jwt", {"bogus": object()})
    assert exc.value.status_code == 422
    assert "Invalid user metadata" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_metadata_other_4xx_propagates_status() -> None:
    with _patched_async_client(_mock_response(429, {"message": "too many"})):
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("fake-jwt", {"timezone": "UTC"})
    assert exc.value.status_code == 429
