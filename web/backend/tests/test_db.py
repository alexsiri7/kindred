"""Unit tests for ``web/backend/db`` GoTrue self-service helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import db


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def _patch_async_client(resp: MagicMock) -> object:
    mock_http = AsyncMock()
    mock_http.put = AsyncMock(return_value=resp)
    mock_cls = patch("db.httpx.AsyncClient")
    started = mock_cls.start()
    started.return_value.__aenter__ = AsyncMock(return_value=mock_http)
    started.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_cls


@pytest.mark.asyncio
async def test_update_user_metadata_returns_metadata_on_success() -> None:
    metadata = {"timezone": "Europe/London", "transcript_enabled": False}
    resp = _mock_response(200, {"user_metadata": metadata})
    cm = _patch_async_client(resp)
    try:
        result = await db.update_user_metadata("fake-jwt", metadata)
    finally:
        cm.stop()
    assert result == metadata


@pytest.mark.asyncio
async def test_update_user_metadata_401_translates_to_http_exception() -> None:
    """Expired JWT (401) must surface as 401 HTTPException, not opaque 500."""
    resp = _mock_response(401, {"message": "Invalid JWT"})
    cm = _patch_async_client(resp)
    try:
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("expired-jwt", {"timezone": "UTC"})
    finally:
        cm.stop()
    assert exc.value.status_code == 401
    assert "Re-authentication" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_metadata_422_translates_to_http_exception() -> None:
    """Malformed metadata (422) must surface as 422 HTTPException, not opaque 500."""
    resp = _mock_response(422, {"message": "bad payload"})
    cm = _patch_async_client(resp)
    try:
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("fake-jwt", {"bogus": object()})
    finally:
        cm.stop()
    assert exc.value.status_code == 422
    assert "Invalid user metadata" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_metadata_other_4xx_propagates_status() -> None:
    resp = _mock_response(429, {"message": "too many"})
    cm = _patch_async_client(resp)
    try:
        with pytest.raises(HTTPException) as exc:
            await db.update_user_metadata("fake-jwt", {"timezone": "UTC"})
    finally:
        cm.stop()
    assert exc.value.status_code == 429
