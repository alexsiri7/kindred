"""Tests for ConnectorTokenVerifier + JWT auth helpers + middleware 401."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest

import db
import settings as settings_module
from auth import ConnectorTokenVerifier, resolve_user_id_from_jwt

SECRET = "test-secret-needs-to-be-at-least-32-bytes-long"
USER_ID = "11111111-2222-3333-4444-555555555555"


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


# ---------------------------------------------------------------------------
# JWT helper
# ---------------------------------------------------------------------------


def test_resolve_user_id_from_jwt_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    token = jwt.encode(
        {"sub": USER_ID, "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp())},
        SECRET,
        algorithm="HS256",
    )
    assert resolve_user_id_from_jwt(token) == USER_ID


def test_resolve_user_id_from_jwt_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    token = jwt.encode(
        {"sub": USER_ID, "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp())},
        SECRET,
        algorithm="HS256",
    )
    assert resolve_user_id_from_jwt(token) is None


def test_resolve_user_id_from_jwt_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    other = "another-secret-also-needs-to-be-at-least-32-bytes"
    token = jwt.encode({"sub": USER_ID}, other, algorithm="HS256")
    assert resolve_user_id_from_jwt(token) is None


def test_resolve_user_id_from_jwt_no_secret_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", "")
    token = jwt.encode({"sub": USER_ID}, "anything-32-bytes-long-here-okay-yes", algorithm="HS256")
    assert resolve_user_id_from_jwt(token) is None


# ---------------------------------------------------------------------------
# Middleware: 401 + WWW-Authenticate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_middleware_returns_401_with_www_authenticate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post("/mcp/")
    assert res.status_code == 401
    www_auth = res.headers.get("www-authenticate", "")
    assert www_auth.startswith("Bearer realm=")
    assert (
        'resource_metadata="https://test.example.com/.well-known/oauth-protected-resource"'
        in www_auth
    )


def test_resolve_user_id_from_jwt_missing_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    token = jwt.encode({"foo": "bar"}, SECRET, algorithm="HS256")
    assert resolve_user_id_from_jwt(token) is None


@pytest.mark.asyncio
async def test_middleware_accepts_valid_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    token = jwt.encode(
        {
            "sub": USER_ID,
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        SECRET,
        algorithm="HS256",
    )
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post("/mcp/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code != 401


@pytest.mark.asyncio
async def test_middleware_falls_through_to_connector_token_when_jwt_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A token starting with 'eyJ' that fails JWT decode must still try DB lookup."""
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )

    fake_token = "eyJnot-a-real-jwt"
    called_with: dict[str, str] = {}

    def _fake_lookup(t: str) -> dict[str, Any]:
        called_with["token"] = t
        return {"user_id": USER_ID, "token": t}

    monkeypatch.setattr(db, "lookup_connector_token", _fake_lookup)
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.post(
            "/mcp/", headers={"Authorization": f"Bearer {fake_token}"}
        )
    assert called_with["token"] == fake_token
    assert res.status_code != 401


@pytest.mark.asyncio
async def test_middleware_resets_contextvar_after_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """current_user_id must NOT leak between requests."""
    from auth import current_user_id

    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    token = jwt.encode(
        {"sub": USER_ID, "exp": 9999999999},
        SECRET,
        algorithm="HS256",
    )
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        await c.post("/mcp/", headers={"Authorization": f"Bearer {token}"})
    with pytest.raises(LookupError):
        current_user_id.get()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expect_401"),
    [
        ("/.well-known/oauth-protected-resource", False),
        ("/.well-known/oauth-authorization-server", False),
        ("/oauth/register", False),
        ("/mcp/", True),
        ("/.well-known", True),
        ("/oauth", True),
        ("/oauth-fake/admin", True),
        ("/oauth/admin", True),
    ],
)
async def test_middleware_public_path_whitelist(
    monkeypatch: pytest.MonkeyPatch, path: str, expect_401: bool
) -> None:
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        res = await c.get(path)
    if expect_401:
        assert res.status_code == 401, f"{path} should be auth-protected"
    else:
        assert res.status_code != 401, f"{path} should bypass auth"
