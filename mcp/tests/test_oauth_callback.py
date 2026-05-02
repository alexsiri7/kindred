"""/oauth/code-from-session endpoint tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest

import oauth_state
import settings as settings_module
from main import app

SUPABASE_JWT_SECRET = "supabase-jwt-secret-needs-to-be-at-least-32-bytes"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )
    monkeypatch.setattr(
        settings_module.settings, "supabase_url", "https://supabase.test.example.com"
    )
    monkeypatch.setattr(settings_module.settings, "supabase_anon_key", "test-anon-key")
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


@pytest.fixture(autouse=True)
def _stub_supabase_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the outbound Supabase /auth/v1/user call.

    Accepts any HS256 JWT signed with ``SUPABASE_JWT_SECRET`` (mirrors what
    real Supabase does — verifies the signature, not the exact byte string).
    Tokens signed with a different secret raise ``PyJWTError`` and the stub
    returns ``None``, preserving the bad-token rejection path.
    """
    import oauth as oauth_module

    async def _fake_verify(access_token: str) -> dict | None:
        try:
            jwt.decode(
                access_token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return None
        return {"id": USER_ID, "email": "u@example.com"}

    monkeypatch.setattr(oauth_module, "_verify_supabase_token", _fake_verify)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _seed_session(flow_id: str, redirect_uri: str = "https://app/cb") -> None:
    oauth_state.oauth_sessions[flow_id] = {
        "client_state": "client-st",
        "redirect_uri": redirect_uri,
        "code_challenge": "ch",
        "code_challenge_method": "S256",
        "client_id": "test-client",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
    }


def _make_supabase_jwt(secret: str = SUPABASE_JWT_SECRET) -> str:
    return jwt.encode(
        {
            "sub": USER_ID,
            "email": "u@example.com",
            "aud": "authenticated",
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        secret,
        algorithm="HS256",
    )


async def test_code_from_session_options_preflight(client: httpx.AsyncClient) -> None:
    res = await client.options(
        "/oauth/code-from-session",
        headers={"Origin": "https://kindred.interstellarai.net"},
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "https://kindred.interstellarai.net"
    assert "POST" in res.headers["access-control-allow-methods"]


async def test_code_from_session_success(client: httpx.AsyncClient) -> None:
    _seed_session("flow-1", "https://app/cb")
    token = _make_supabase_jwt()

    res = await client.post(
        "/oauth/code-from-session",
        json={"flow_id": "flow-1", "access_token": token},
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "https://kindred.interstellarai.net"

    body = res.json()
    assert "redirect_url" in body
    parsed = urlparse(body["redirect_url"])
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://app/cb"
    qs = parse_qs(parsed.query)
    assert "code" in qs
    assert qs["state"] == ["client-st"]

    kindred_code = qs["code"][0]
    assert kindred_code in oauth_state.auth_codes
    assert oauth_state.auth_codes[kindred_code]["user_id"] == USER_ID


async def test_code_from_session_invalid_flow_id(client: httpx.AsyncClient) -> None:
    token = _make_supabase_jwt()
    res = await client.post(
        "/oauth/code-from-session",
        json={"flow_id": "does-not-exist", "access_token": token},
    )
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_request"


async def test_code_from_session_bad_jwt(client: httpx.AsyncClient) -> None:
    _seed_session("flow-2")
    bad_token = _make_supabase_jwt(secret="different-secret-which-is-also-32-bytes-long")
    res = await client.post(
        "/oauth/code-from-session",
        json={"flow_id": "flow-2", "access_token": bad_token},
    )
    assert res.status_code == 400
    assert res.json()["error"] == "server_error"


async def test_code_from_session_missing_fields(client: httpx.AsyncClient) -> None:
    res = await client.post("/oauth/code-from-session", json={"flow_id": "x"})
    assert res.status_code == 400


async def test_code_from_session_flow_id_is_single_use(client: httpx.AsyncClient) -> None:
    _seed_session("flow-3")
    token = _make_supabase_jwt()
    r1 = await client.post(
        "/oauth/code-from-session",
        json={"flow_id": "flow-3", "access_token": token},
    )
    r2 = await client.post(
        "/oauth/code-from-session",
        json={"flow_id": "flow-3", "access_token": token},
    )
    assert r1.status_code == 200
    assert r2.status_code == 400
