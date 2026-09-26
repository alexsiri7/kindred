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

import oauth
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


async def test_authorize_redirects_to_web_app_relay(client: httpx.AsyncClient) -> None:
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
    assert loc.startswith("https://kindred.interstellarai.net/mcp-auth?flow=")
    flow_key = parse_qs(urlparse(loc).query)["flow"][0]
    assert flow_key in oauth_state.oauth_sessions
    assert oauth_state.oauth_sessions[flow_key]["client_state"] == "client-state-123"
    assert oauth_state.oauth_sessions[flow_key]["redirect_uri"] == "https://app/cb"


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


PUBLIC_CLIENT_ID = "test-client"
CONF_CLIENT_ID = "conf-client"
CONF_SECRET = "conf-secret-value"


def _seed_client(client_id: str, method: str, secret: str = "unused-secret") -> None:
    oauth_state.registered_clients[client_id] = {
        "client_id": client_id,
        "client_secret": secret,
        "redirect_uris": ["https://app/cb"],
        "client_name": client_id,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": method,
        "scope": "mcp",
    }


@pytest.fixture(autouse=True)
def _seed_public_client(_clear_state: None) -> None:
    _seed_client(PUBLIC_CLIENT_ID, "none")


def _seed_auth_code(
    *, code: str, verifier: str, redirect_uri: str, client_id: str = PUBLIC_CLIENT_ID
) -> None:
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
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
            "client_id": "test-client",
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
    }
    r1 = await client.post("/oauth/token", data=data)
    r2 = await client.post("/oauth/token", data=data)
    assert r1.status_code == 200
    assert r2.status_code == 400


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
        },
    )
    refresh_1 = r1.json()["refresh_token"]

    r2 = await client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_1},
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
        data={"grant_type": "refresh_token", "refresh_token": refresh_1},
    )
    assert r3.status_code == 400


async def test_token_rotation_calls_delete_refresh_token(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token rotation (refresh_token grant) must call delete_refresh_token() on consumed token."""
    deleted: list[str] = []
    monkeypatch.setattr(oauth, "delete_refresh_token", lambda t: deleted.append(t))

    verifier, _ = _pkce_pair()
    _seed_auth_code(code="ac-del", verifier=verifier, redirect_uri="https://app/cb")
    r1 = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": "ac-del",
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
        },
    )
    assert r1.status_code == 200
    refresh_token_1 = r1.json()["refresh_token"]

    r2 = await client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token_1},
    )
    assert r2.status_code == 200
    assert deleted == [refresh_token_1]


# ---------------------------------------------------------------------------
# /oauth/token (refresh_token) — client authentication
# ---------------------------------------------------------------------------


async def _issue_refresh(client: httpx.AsyncClient, code: str, client_id: str) -> str:
    verifier, _ = _pkce_pair()
    _seed_auth_code(
        code=code, verifier=verifier, redirect_uri="https://app/cb", client_id=client_id
    )
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://app/cb",
            "code_verifier": verifier,
            "client_id": client_id,
        },
    )
    assert res.status_code == 200
    return str(res.json()["refresh_token"])


async def test_refresh_confidential_client_requires_secret(client: httpx.AsyncClient) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_post", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c1", CONF_CLIENT_ID)
    res = await client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": rt, "client_id": CONF_CLIENT_ID},
    )
    assert res.status_code == 401
    # A failed authentication must not consume the refresh token.
    assert rt in oauth_state.refresh_tokens


async def test_refresh_confidential_client_rejects_wrong_secret(
    client: httpx.AsyncClient,
) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_post", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c2", CONF_CLIENT_ID)
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": CONF_CLIENT_ID,
            "client_secret": "wrong",
        },
    )
    assert res.status_code == 401
    assert rt in oauth_state.refresh_tokens


async def test_refresh_confidential_client_rejects_missing_credentials(
    client: httpx.AsyncClient,
) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_post", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c3", CONF_CLIENT_ID)
    res = await client.post(
        "/oauth/token", data={"grant_type": "refresh_token", "refresh_token": rt}
    )
    assert res.status_code == 401


async def test_refresh_confidential_client_post_secret_succeeds(
    client: httpx.AsyncClient,
) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_post", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c4", CONF_CLIENT_ID)
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": CONF_CLIENT_ID,
            "client_secret": CONF_SECRET,
        },
    )
    assert res.status_code == 200
    assert rt not in oauth_state.refresh_tokens


async def test_refresh_confidential_client_basic_auth_succeeds(
    client: httpx.AsyncClient,
) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_basic", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c5", CONF_CLIENT_ID)
    basic = base64.b64encode(f"{CONF_CLIENT_ID}:{CONF_SECRET}".encode()).decode()
    res = await client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": rt},
        headers={"Authorization": f"Basic {basic}"},
    )
    assert res.status_code == 200


async def test_refresh_rejects_other_clients_token(client: httpx.AsyncClient) -> None:
    _seed_client(CONF_CLIENT_ID, "client_secret_post", CONF_SECRET)
    rt = await _issue_refresh(client, "ac-c6", PUBLIC_CLIENT_ID)
    res = await client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": CONF_CLIENT_ID,
            "client_secret": CONF_SECRET,
        },
    )
    assert res.status_code == 400
    assert rt in oauth_state.refresh_tokens


async def test_refresh_public_client_with_matching_client_id(client: httpx.AsyncClient) -> None:
    rt = await _issue_refresh(client, "ac-p1", PUBLIC_CLIENT_ID)
    res = await client.post(
        "/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": rt, "client_id": PUBLIC_CLIENT_ID},
    )
    assert res.status_code == 200


async def test_refresh_rejects_unregistered_client(client: httpx.AsyncClient) -> None:
    rt = await _issue_refresh(client, "ac-p2", PUBLIC_CLIENT_ID)
    oauth_state.registered_clients.pop(PUBLIC_CLIENT_ID)
    res = await client.post(
        "/oauth/token", data={"grant_type": "refresh_token", "refresh_token": rt}
    )
    assert res.status_code == 401
