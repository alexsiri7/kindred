"""Callback endpoint tests — Supabase token exchange + JWT decode."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest

import oauth as oauth_module
import oauth_state
import settings as settings_module
from main import app

SUPABASE_JWT_SECRET = "supabase-jwt-secret-needs-to-be-at-least-32-bytes"
SUPABASE_URL = "https://supabase.test"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    monkeypatch.setattr(settings_module.settings, "supabase_url", SUPABASE_URL)
    monkeypatch.setattr(settings_module.settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(
        settings_module.settings, "supabase_jwt_secret", SUPABASE_JWT_SECRET
    )
    monkeypatch.setattr(
        settings_module.settings,
        "secret_key",
        "kindred-secret-needs-to-be-at-least-32-bytes!",
    )


@pytest.fixture(autouse=True)
def _clear_state() -> None:
    oauth_state.oauth_sessions.clear()
    oauth_state.auth_codes.clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _seed_session(server_state: str, redirect_uri: str = "https://app/cb") -> None:
    oauth_state.oauth_sessions[server_state] = {
        "client_state": "client-st",
        "redirect_uri": redirect_uri,
        "code_challenge": "ch",
        "code_challenge_method": "S256",
        "client_id": "test-client",
        "scope": "mcp",
        "supabase_code_verifier": "verifier-xyz",
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
    }


class _StubResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    """Minimal stand-in for ``httpx.AsyncClient`` used inside ``oauth.py``."""

    response: _StubResponse = _StubResponse(200, {})

    def __init__(self, *_args: Any, **_kw: Any) -> None: ...

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc: Any) -> None: ...

    async def post(self, *_args: Any, **_kw: Any) -> _StubResponse:
        return type(self).response


def _make_supabase_jwt() -> str:
    return jwt.encode(
        {
            "sub": USER_ID,
            "email": "u@example.com",
            "aud": "authenticated",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )


async def test_callback_success_redirects_with_kindred_code(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    _seed_session("server-state-1", "https://app/cb")
    supabase_jwt = _make_supabase_jwt()
    _FakeAsyncClient.response = _StubResponse(200, {"access_token": supabase_jwt})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    res = await client.get(
        "/oauth/callback",
        params={"code": "supabase-code", "state": "server-state-1"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    parsed = urlparse(res.headers["location"])
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://app/cb"
    qs = parse_qs(parsed.query)
    assert "code" in qs
    assert qs["state"] == ["client-st"]
    # an auth code entry was minted with the right user_id
    kindred_code = qs["code"][0]
    assert kindred_code in oauth_state.auth_codes
    assert oauth_state.auth_codes[kindred_code]["user_id"] == USER_ID


async def test_callback_supabase_400_redirects_with_error(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    _seed_session("server-state-2")
    _FakeAsyncClient.response = _StubResponse(400, {"error": "invalid_grant"})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "server-state-2"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["server_error"]


async def test_callback_unknown_state_returns_400(client: httpx.AsyncClient) -> None:
    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "never-seeded"},
        follow_redirects=False,
    )
    assert res.status_code == 400


async def test_callback_jwt_decode_failure_redirects_with_error(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    _seed_session("server-state-3")
    # access_token signed with a *different* secret → decode will fail
    bad_jwt = jwt.encode(
        {"sub": USER_ID, "aud": "authenticated"},
        "different-secret-which-is-also-32-bytes-long",
        algorithm="HS256",
    )
    _FakeAsyncClient.response = _StubResponse(200, {"access_token": bad_jwt})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "server-state-3"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["server_error"]


async def test_callback_state_is_single_use(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    """Replaying the same state must fail — guards against OAuth state CSRF."""
    _seed_session("server-state-replay")
    supabase_jwt = _make_supabase_jwt()
    _FakeAsyncClient.response = _StubResponse(200, {"access_token": supabase_jwt})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    r1 = await client.get(
        "/oauth/callback",
        params={"code": "supabase-code", "state": "server-state-replay"},
        follow_redirects=False,
    )
    r2 = await client.get(
        "/oauth/callback",
        params={"code": "supabase-code", "state": "server-state-replay"},
        follow_redirects=False,
    )
    assert r1.status_code == 302
    assert r2.status_code == 400


async def test_callback_missing_supabase_code_redirects_invalid_request(
    client: httpx.AsyncClient,
) -> None:
    _seed_session("server-state-no-code")
    res = await client.get(
        "/oauth/callback",
        params={"state": "server-state-no-code"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["invalid_request"]


async def test_callback_supabase_response_missing_access_token(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    _seed_session("server-state-no-at")
    _FakeAsyncClient.response = _StubResponse(200, {"unexpected": "shape"})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "server-state-no-at"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["server_error"]


async def test_callback_supabase_jwt_missing_sub(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    _seed_session("server-state-no-sub")
    no_sub_jwt = jwt.encode(
        {
            "aud": "authenticated",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )
    _FakeAsyncClient.response = _StubResponse(200, {"access_token": no_sub_jwt})
    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _FakeAsyncClient)

    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "server-state-no-sub"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["server_error"]


async def test_callback_httpx_error_redirects_server_error(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    """Transient Supabase outage must return a clean redirect, not a 500."""
    _seed_session("server-state-httpx-err")

    class _ExplodingClient(_FakeAsyncClient):
        async def post(self, *_args: Any, **_kw: Any) -> _StubResponse:
            raise httpx.ConnectError("Supabase unreachable")

    monkeypatch.setattr(oauth_module.httpx, "AsyncClient", _ExplodingClient)
    res = await client.get(
        "/oauth/callback",
        params={"code": "x", "state": "server-state-httpx-err"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["server_error"]
