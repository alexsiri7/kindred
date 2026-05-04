"""Tests for ConnectorTokenVerifier + JWT auth helpers + middleware 401."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
from lib import db
from lib.services import tokens

import settings as settings_module
from auth import ConnectorTokenVerifier, resolve_user_id_from_jwt

SECRET = "test-secret-needs-to-be-at-least-32-bytes-long"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.mark.asyncio
async def test_verify_token_unknown_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifecycle (#41): the lookup RPC returns NULL for unknown, revoked,
    AND expired tokens — all three collapse to the same constant-shape
    miss. The verifier returns None for any of them, the middleware
    translates that to 401. No MCP code change is needed for the
    lifecycle work; the RPC handles it.
    """
    monkeypatch.setattr(tokens, "lookup_token", lambda _t: None)
    verifier = ConnectorTokenVerifier()
    assert await verifier.verify_token("does-not-exist") is None


@pytest.mark.asyncio
async def test_lookup_token_rpc_none_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anon RPC returning NULL → verifier returns None (no exception)."""

    class _RpcResp:
        data = None

    class _RpcChain:
        def execute(self) -> _RpcResp:
            return _RpcResp()

    class _Client:
        def rpc(self, _name: str, _params: dict[str, Any]) -> _RpcChain:
            return _RpcChain()

    monkeypatch.setattr(db, "anon_client", lambda: _Client())
    assert tokens.lookup_token("missing") is None
    verifier = ConnectorTokenVerifier()
    assert await verifier.verify_token("missing") is None


@pytest.mark.asyncio
async def test_verify_token_known_returns_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = "11111111-2222-3333-4444-555555555555"

    def _fake_lookup(_t: str) -> str:
        return user_id

    monkeypatch.setattr(tokens, "lookup_token", _fake_lookup)
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
