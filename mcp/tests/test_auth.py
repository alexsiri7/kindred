"""Tests for ConnectorTokenVerifier + JWT auth helpers + 401 middleware."""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
import pytest

import db
import settings as settings_module
from auth import ConnectorTokenVerifier, resolve_user_id, resolve_user_id_from_jwt
from oauth.state import canonical_resource_url

SECRET = "test-secret-needs-to-be-at-least-32-bytes-long"
USER_ID = "11111111-2222-3333-4444-555555555555"
BASE_URL = "https://test.example.com"


def _mint(secret: str, sub: str, *, audience: str | None = None, exp_offset: int = 3600) -> str:
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    if audience is not None:
        payload["aud"] = audience
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_verify_token_unknown_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "lookup_connector_token", lambda _t: None)
    verifier = ConnectorTokenVerifier()
    assert await verifier.verify_token("does-not-exist") is None


@pytest.mark.asyncio
async def test_verify_token_known_returns_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_lookup(_t: str) -> dict[str, Any]:
        return {"user_id": USER_ID, "token": _t}

    monkeypatch.setattr(db, "lookup_connector_token", _fake_lookup)
    verifier = ConnectorTokenVerifier()
    token = await verifier.verify_token("good-token")
    assert token is not None
    assert token.client_id == USER_ID
    assert token.scopes == ["user"]
    assert token.expires_at is None


# ---------------------------------------------------------------------------
# JWT helper (audience-validating)
# ---------------------------------------------------------------------------


def _configure_jwt_settings(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE_URL)
    return canonical_resource_url()


def test_resolve_user_id_from_jwt_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    aud = _configure_jwt_settings(monkeypatch)
    token = _mint(SECRET, USER_ID, audience=aud)
    assert resolve_user_id_from_jwt(token) == USER_ID


def test_resolve_user_id_from_jwt_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    aud = _configure_jwt_settings(monkeypatch)
    token = _mint(SECRET, USER_ID, audience=aud, exp_offset=-3600)
    assert resolve_user_id_from_jwt(token) is None


def test_resolve_user_id_from_jwt_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_jwt_settings(monkeypatch)
    token = _mint(SECRET, USER_ID, audience="https://other.example.com/mcp")
    assert resolve_user_id_from_jwt(token) is None


def test_resolve_user_id_from_jwt_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    aud = _configure_jwt_settings(monkeypatch)
    token = _mint("a-different-secret-also-32-bytes-long", USER_ID, audience=aud)
    assert resolve_user_id_from_jwt(token) is None


def test_resolve_user_id_from_jwt_no_secret_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", "")
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE_URL)
    token = _mint(
        "another-secret-also-32-bytes-long-padding",
        USER_ID,
        audience=canonical_resource_url(),
    )
    assert resolve_user_id_from_jwt(token) is None


@pytest.mark.asyncio
async def test_resolve_user_id_falls_back_to_connector_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "lookup_connector_token", lambda _t: {"user_id": USER_ID})
    assert await resolve_user_id("opaque-connector-token") == USER_ID


@pytest.mark.asyncio
async def test_resolve_user_id_unknown_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(db, "lookup_connector_token", lambda _t: None)
    assert await resolve_user_id("does-not-exist") is None


# ---------------------------------------------------------------------------
# Middleware: 401 + WWW-Authenticate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_middleware_returns_401_with_www_authenticate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE_URL)
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post("/mcp/")
    assert res.status_code == 401
    www_auth = res.headers.get("www-authenticate", "")
    assert www_auth.startswith("Bearer realm=")
    assert (
        f'resource_metadata="{BASE_URL}/.well-known/oauth-protected-resource"' in www_auth
    )


@pytest.mark.asyncio
async def test_middleware_passes_health_check_through() -> None:
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
