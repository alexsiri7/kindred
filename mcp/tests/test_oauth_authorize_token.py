"""Authorize → Token end-to-end tests (PKCE + refresh-token rotation)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest

import oauth_state
import settings as settings_module
from main import app

SECRET = "test-secret-do-not-use-in-prod-needs-32-bytes-minimum"
SUPABASE_URL = "https://supabase.test"
BASE = "https://test.example.com"
USER_ID = "11111111-2222-3333-4444-555555555555"


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE)
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(settings_module.settings, "supabase_url", SUPABASE_URL)


@pytest.fixture(autouse=True)
def _clear_state() -> None:
    oauth_state.registered_clients.clear()
    oauth_state.oauth_sessions.clear()
    oauth_state.auth_codes.clear()
    oauth_state.refresh_tokens.clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _register(client: httpx.AsyncClient, redirect: str = "https://app/cb") -> str:
    res = await client.post(
        "/oauth/register",
        json={"client_name": "test", "redirect_uris": [redirect]},
    )
    assert res.status_code == 201
    return str(res.json()["client_id"])


# ---------------------------------------------------------------------------
# /oauth/authorize
# ---------------------------------------------------------------------------


async def test_authorize_redirects_to_supabase(client: httpx.AsyncClient) -> None:
    cid = await _register(client)
    _verifier, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "redirect_uri": "https://app/cb",
            "state": "client-state-123",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "response_type": "code",
            "scope": "mcp",
        },
        follow_redirects=False,
    )
    assert res.status_code == 302
    loc = res.headers["location"]
    assert loc.startswith(f"{SUPABASE_URL}/auth/v1/authorize?")
    qs = parse_qs(urlparse(loc).query)
    assert qs["provider"] == ["google"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["redirect_to"] == [f"{BASE}/oauth/callback"]
    assert "state" in qs
    # Server state must be stored in the sessions dict
    server_state = qs["state"][0]
    assert server_state in oauth_state.oauth_sessions
    assert oauth_state.oauth_sessions[server_state]["client_state"] == "client-state-123"


async def test_authorize_rejects_unknown_redirect_uri(client: httpx.AsyncClient) -> None:
    cid = await _register(client, redirect="https://app/cb")
    _v, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "redirect_uri": "https://evil.com/cb",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


async def test_authorize_rejects_missing_code_challenge(client: httpx.AsyncClient) -> None:
    cid = await _register(client)
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "redirect_uri": "https://app/cb",
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


async def test_authorize_rejects_plain_pkce(client: httpx.AsyncClient) -> None:
    cid = await _register(client)
    _v, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "redirect_uri": "https://app/cb",
            "code_challenge": challenge,
            "code_challenge_method": "plain",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


async def test_authorize_rejects_unknown_client_id(client: httpx.AsyncClient) -> None:
    _v, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": "does-not-exist",
            "redirect_uri": "https://app/cb",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# /oauth/token (authorization_code)
# ---------------------------------------------------------------------------


TEST_CLIENT_ID = "test-client"
TEST_CLIENT_SECRET = "test-client-secret-do-not-use"


def _seed_auth_code(
    *,
    code: str,
    verifier: str,
    redirect_uri: str,
    client_id: str = TEST_CLIENT_ID,
) -> None:
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    oauth_state.registered_clients.setdefault(
        client_id,
        {
            "client_id": client_id,
            "client_secret": TEST_CLIENT_SECRET,
            "redirect_uris": [redirect_uri],
            "client_name": "test",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
            "scope": "mcp",
        },
    )
    oauth_state.auth_codes[code] = {
        "user_id": USER_ID,
        "email": "u@example.com",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "redirect_uri": redirect_uri,
        "scope": "mcp",
        "client_id": client_id,
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
    }


async def test_token_authorization_code_returns_jwt(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-1", verifier=verifier, redirect_uri="https://app/cb")
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-1",
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body and "refresh_token" in body
    claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == USER_ID
    assert claims["email"] == "u@example.com"


async def test_token_rejects_wrong_verifier(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-2", verifier=verifier, redirect_uri="https://app/cb")
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-2",
            "redirect_uri": "https://app/cb",
            "code_verifier": "the-wrong-verifier",
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 400


async def test_token_rejects_redirect_uri_mismatch(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-3", verifier=verifier, redirect_uri="https://app/cb")
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-3",
            "redirect_uri": "https://wrong.example/cb",
            "code_verifier": verifier,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 400


async def test_token_auth_code_is_single_use(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-4", verifier=verifier, redirect_uri="https://app/cb")
    data = {
        "grant_type": "authorization_code",
        "code": "ac-4",
        "redirect_uri": "https://app/cb",
        "code_verifier": verifier,
        "client_id": TEST_CLIENT_ID,
        "client_secret": TEST_CLIENT_SECRET,
    }
    r1 = await client.post("/oauth/token", data=data)
    r2 = await client.post("/oauth/token", data=data)
    assert r1.status_code == 200
    assert r2.status_code == 400


async def test_token_rejects_invalid_client_secret(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-bad-secret", verifier=verifier, redirect_uri="https://app/cb")
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-bad-secret",
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
            "client_id": TEST_CLIENT_ID,
            "client_secret": "wrong-secret",
        },
    )
    assert res.status_code == 401


async def test_token_rejects_missing_client_id(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-no-client", verifier=verifier, redirect_uri="https://app/cb")
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-no-client",
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
        },
    )
    assert res.status_code == 401


def _register_test_client_in_state() -> None:
    oauth_state.registered_clients[TEST_CLIENT_ID] = {
        "client_id": TEST_CLIENT_ID,
        "client_secret": TEST_CLIENT_SECRET,
        "redirect_uris": ["https://app/cb"],
        "client_name": "test",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
        "scope": "mcp",
    }


async def test_token_rejects_unsupported_grant_type(client: httpx.AsyncClient) -> None:
    _register_test_client_in_state()
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 400


async def test_token_refresh_rejects_missing_token(client: httpx.AsyncClient) -> None:
    _register_test_client_in_state()
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 400


async def test_token_rejects_missing_code_verifier(client: httpx.AsyncClient) -> None:
    """Auth code seeded with S256 challenge — token request must include verifier."""
    verifier, _ = _pkce_pair()
    _seed_auth_code(
        code="ac-no-verifier", verifier=verifier, redirect_uri="https://app/cb"
    )
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-no-verifier",
            "redirect_uri": "https://app/cb",
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert res.status_code == 400


async def test_authorize_returns_501_when_secret_key_unset(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", "")
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": "x",
            "redirect_uri": "https://app/cb",
            "code_challenge": "c",
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert res.status_code == 501


async def test_authorize_rejects_unsupported_response_type(
    client: httpx.AsyncClient,
) -> None:
    cid = await _register(client)
    _v, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "redirect_uri": "https://app/cb",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "response_type": "token",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


async def test_authorize_rejects_missing_redirect_uri(
    client: httpx.AsyncClient,
) -> None:
    cid = await _register(client)
    _v, challenge = _pkce_pair()
    res = await client.get(
        "/oauth/authorize",
        params={
            "client_id": cid,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# /oauth/token (refresh_token)
# ---------------------------------------------------------------------------


async def test_refresh_token_rotation(client: httpx.AsyncClient) -> None:
    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-5", verifier=verifier, redirect_uri="https://app/cb")
    r1 = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-5",
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    refresh_1 = r1.json()["refresh_token"]

    r2 = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_1,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert r2.status_code == 200
    body = r2.json()
    refresh_2 = body["refresh_token"]
    assert refresh_2 != refresh_1
    claims = jwt.decode(body["access_token"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == USER_ID

    # Old refresh token must now be rejected (single-use rotation).
    r3 = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_1,
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
    )
    assert r3.status_code == 400
