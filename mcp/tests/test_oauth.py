"""Tests for the six OAuth + discovery endpoints, PKCE, and JWT issuance."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest

import settings as settings_module
from oauth import state as oauth_state
from oauth.state import (
    canonical_resource_url,
    derive_pkce_s256_challenge,
    mint_access_jwt,
    verify_access_jwt,
    verify_pkce_s256,
)

SECRET = "test-secret-needs-to-be-at-least-32-bytes-long"
BASE_URL = "https://test.example.com"
SUPABASE_URL = "https://supa.example.com"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE_URL)
    monkeypatch.setattr(settings_module.settings, "supabase_url", SUPABASE_URL)
    monkeypatch.setattr(settings_module.settings, "supabase_anon_key", "anon-key")
    oauth_state._reset_all_for_tests()
    yield
    oauth_state._reset_all_for_tests()


@pytest.fixture
def client() -> Iterator[httpx.AsyncClient]:
    from main import app

    yield httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# PKCE / JWT helpers
# ---------------------------------------------------------------------------


def test_pkce_s256_roundtrip() -> None:
    verifier = "abc" + "x" * 60
    challenge = derive_pkce_s256_challenge(verifier)
    assert verify_pkce_s256(verifier, challenge) is True
    assert verify_pkce_s256(verifier, challenge + "tampered") is False
    assert verify_pkce_s256(verifier + "wrong", challenge) is False


def test_mint_and_verify_access_jwt_roundtrip() -> None:
    aud = canonical_resource_url()
    token = mint_access_jwt(user_id=USER_ID, audience=aud)
    assert verify_access_jwt(token, expected_audience=aud) == USER_ID


def test_verify_access_jwt_wrong_audience_returns_none() -> None:
    token = mint_access_jwt(user_id=USER_ID, audience=canonical_resource_url())
    assert verify_access_jwt(token, expected_audience="https://other/mcp") is None


def test_verify_access_jwt_expired_returns_none() -> None:
    aud = canonical_resource_url()
    token = mint_access_jwt(user_id=USER_ID, audience=aud, expires_in_s=-10)
    assert verify_access_jwt(token, expected_audience=aud) is None


def test_verify_access_jwt_logs_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Operators need the failure reason in logs to diagnose misconfiguration
    (e.g., a wrong SECRET_KEY) without leaking the token bytes."""
    import logging

    aud = canonical_resource_url()
    token = mint_access_jwt(user_id=USER_ID, audience=aud)
    with caplog.at_level(logging.INFO, logger="oauth.state"):
        assert verify_access_jwt(token, expected_audience="https://other/mcp") is None
    assert any(
        "JWT verification failed" in r.message and "InvalidAudienceError" in r.message
        for r in caplog.records
    )


def test_canonical_resource_url_raises_when_base_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty MCP_BASE_URL would mint JWTs with aud='/mcp', defeating RFC 8707
    audience binding. Fail loud instead of silently producing a relative URL."""
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", "")
    with pytest.raises(RuntimeError, match="MCP_BASE_URL"):
        canonical_resource_url()


# ---------------------------------------------------------------------------
# Discovery endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_protected_resource_metadata(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.get("/.well-known/oauth-protected-resource")
    assert res.status_code == 200
    body = res.json()
    assert body["resource"] == canonical_resource_url()
    assert body["authorization_servers"] == [BASE_URL]
    assert body["scopes_supported"] == ["mcp"]
    assert body["bearer_methods_supported"] == ["header"]


@pytest.mark.asyncio
async def test_authorization_server_metadata(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.get("/.well-known/oauth-authorization-server")
    assert res.status_code == 200
    body = res.json()
    assert body["issuer"] == BASE_URL
    assert body["authorization_endpoint"] == f"{BASE_URL}/oauth/authorize"
    assert body["token_endpoint"] == f"{BASE_URL}/oauth/token"
    assert body["registration_endpoint"] == f"{BASE_URL}/oauth/register"
    assert body["code_challenge_methods_supported"] == ["S256"]
    assert "authorization_code" in body["grant_types_supported"]
    assert "refresh_token" in body["grant_types_supported"]
    assert body["token_endpoint_auth_methods_supported"] == ["none"]


# ---------------------------------------------------------------------------
# Dynamic Client Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_happy_path(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.post(
            "/oauth/register",
            json={
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
                "client_name": "Claude.ai",
            },
        )
    assert res.status_code == 201
    body = res.json()
    assert body["client_id"]
    # Public clients (token_endpoint_auth_method=none) MUST NOT receive a
    # client_secret in the registration response — RFC 7591 §3.2.1.
    assert "client_secret" not in body
    assert "authorization_code" in body["grant_types"]
    assert "refresh_token" in body["grant_types"]
    assert body["token_endpoint_auth_method"] == "none"


@pytest.mark.asyncio
async def test_register_rejects_empty_redirect_uris(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.post("/oauth/register", json={"redirect_uris": []})
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_register_rejects_non_json_body(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.post(
            "/oauth/register",
            content=b"not-json",
            headers={"content-type": "application/json"},
        )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# /oauth/authorize
# ---------------------------------------------------------------------------


async def _register(c: httpx.AsyncClient, redirect_uri: str) -> str:
    res = await c.post(
        "/oauth/register",
        json={"redirect_uris": [redirect_uri], "client_name": "test"},
    )
    return str(res.json()["client_id"])


@pytest.mark.asyncio
async def test_authorize_rejects_plain_pkce(client: httpx.AsyncClient) -> None:
    async with client as c:
        client_id = await _register(c, "https://app/cb")
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
                "response_type": "code",
                "code_challenge": "anything",
                "code_challenge_method": "plain",
                "state": "csrf",
            },
        )
    # RFC 6749 §4.1.2.1: post-redirect-validation errors redirect with ?error=.
    assert res.status_code == 302
    parsed = urlparse(res.headers["location"])
    qs = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://app/cb"
    assert qs["error"] == ["invalid_request"]
    assert qs["state"] == ["csrf"]


@pytest.mark.asyncio
async def test_authorize_rejects_unknown_client(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": "no-such-client",
                "redirect_uri": "https://app/cb",
                "response_type": "code",
                "code_challenge": "anything",
                "code_challenge_method": "S256",
            },
        )
    # RFC 6749 §4.1.2.1: pre-redirect-validation errors return JSON, NOT a
    # redirect — never bounce to an unverified redirect_uri.
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_client"


@pytest.mark.asyncio
async def test_authorize_rejects_unregistered_redirect_uri(
    client: httpx.AsyncClient,
) -> None:
    async with client as c:
        client_id = await _register(c, "https://app/cb")
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://attacker.example/cb",
                "response_type": "code",
                "code_challenge": "anything",
                "code_challenge_method": "S256",
            },
        )
    # Pre-redirect-validation: don't bounce to a redirect_uri we haven't
    # validated against the registered set.
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_authorize_redirects_with_error_for_unsupported_response_type(
    client: httpx.AsyncClient,
) -> None:
    async with client as c:
        client_id = await _register(c, "https://app/cb")
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
                "response_type": "token",
                "code_challenge": derive_pkce_s256_challenge("v" * 64),
                "code_challenge_method": "S256",
                "state": "csrf",
            },
        )
    assert res.status_code == 302
    parsed = urlparse(res.headers["location"])
    qs = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://app/cb"
    assert qs["error"] == ["unsupported_response_type"]
    assert qs["state"] == ["csrf"]


@pytest.mark.asyncio
async def test_authorize_redirects_with_error_omits_state_when_absent(
    client: httpx.AsyncClient,
) -> None:
    async with client as c:
        client_id = await _register(c, "https://app/cb")
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
                "response_type": "code",
                "code_challenge": "anything",
                "code_challenge_method": "plain",
            },
        )
    assert res.status_code == 302
    qs = parse_qs(urlparse(res.headers["location"]).query)
    assert qs["error"] == ["invalid_request"]
    assert "state" not in qs


@pytest.mark.asyncio
async def test_authorize_redirects_to_supabase(client: httpx.AsyncClient) -> None:
    async with client as c:
        client_id = await _register(c, "https://app/cb")
        res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
                "response_type": "code",
                "code_challenge": derive_pkce_s256_challenge("v" * 64),
                "code_challenge_method": "S256",
                "state": "csrf-token",
            },
        )
    assert res.status_code == 302
    location = res.headers["location"]
    parsed = urlparse(location)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "supa.example.com"
    assert qs["provider"] == ["google"]
    assert qs["redirect_to"] == [f"{BASE_URL}/oauth/callback"]
    assert qs["code_challenge_method"] == ["S256"]
    assert "state" in qs


# ---------------------------------------------------------------------------
# /oauth/callback (Supabase exchange monkey-patched)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callback_redirects_with_kindred_code(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    from oauth import supabase as oauth_supabase

    async def _fake_exchange(_code: str, _verifier: str) -> str:
        return USER_ID

    monkeypatch.setattr(oauth_supabase, "exchange_code", _fake_exchange)

    async with client as c:
        client_id = await _register(c, "https://app/cb")
        verifier = "ver-" + "x" * 60
        challenge = derive_pkce_s256_challenge(verifier)
        auth_res = await c.get(
            "/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
                "response_type": "code",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": "csrf",
            },
        )
        # Recover the kindred-side state that was passed onward to Supabase.
        upstream_state = parse_qs(urlparse(auth_res.headers["location"]).query)["state"][0]
        cb_res = await c.get(
            "/oauth/callback",
            params={"code": "supabase-code", "state": upstream_state},
        )
    assert cb_res.status_code == 302
    target = urlparse(cb_res.headers["location"])
    target_qs = parse_qs(target.query)
    assert f"{target.scheme}://{target.netloc}{target.path}" == "https://app/cb"
    assert target_qs["state"] == ["csrf"]
    assert target_qs["code"][0]


@pytest.mark.asyncio
async def test_callback_unknown_state_rejected(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.get("/oauth/callback", params={"code": "x", "state": "nope"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# /oauth/token: authorization_code + refresh_token
# ---------------------------------------------------------------------------


async def _full_authorize_and_callback(
    monkeypatch: pytest.MonkeyPatch, c: httpx.AsyncClient, *, verifier: str
) -> tuple[str, str]:
    """Drive /authorize → /callback (mocked) and return (client_id, kindred_code)."""
    from oauth import supabase as oauth_supabase

    async def _fake_exchange(_code: str, _verifier: str) -> str:
        return USER_ID

    monkeypatch.setattr(oauth_supabase, "exchange_code", _fake_exchange)

    client_id = await _register(c, "https://app/cb")
    challenge = derive_pkce_s256_challenge(verifier)
    auth_res = await c.get(
        "/oauth/authorize",
        params={
            "client_id": client_id,
            "redirect_uri": "https://app/cb",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "csrf",
        },
    )
    upstream_state = parse_qs(urlparse(auth_res.headers["location"]).query)["state"][0]
    cb_res = await c.get(
        "/oauth/callback", params={"code": "supabase-code", "state": upstream_state}
    )
    kindred_code = parse_qs(urlparse(cb_res.headers["location"]).query)["code"][0]
    return client_id, kindred_code


@pytest.mark.asyncio
async def test_token_authorization_code_happy_path(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    verifier = "ver-" + "x" * 60
    async with client as c:
        client_id, kindred_code = await _full_authorize_and_callback(
            monkeypatch, c, verifier=verifier
        )
        res = await c.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": kindred_code,
                "code_verifier": verifier,
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
            },
        )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "Bearer"
    assert body["scope"] == "mcp"
    assert body["expires_in"] == 3600
    assert body["refresh_token"]
    decoded: dict[str, Any] = jwt.decode(
        body["access_token"],
        SECRET,
        algorithms=["HS256"],
        audience=canonical_resource_url(),
    )
    assert decoded["sub"] == USER_ID
    assert decoded["aud"] == canonical_resource_url()
    assert decoded["scope"] == "mcp"
    assert decoded["iss"] == BASE_URL
    assert decoded["exp"] > int(time.time())


@pytest.mark.asyncio
async def test_token_rejects_reused_code(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    verifier = "ver-" + "x" * 60
    async with client as c:
        client_id, kindred_code = await _full_authorize_and_callback(
            monkeypatch, c, verifier=verifier
        )
        data = {
            "grant_type": "authorization_code",
            "code": kindred_code,
            "code_verifier": verifier,
            "client_id": client_id,
            "redirect_uri": "https://app/cb",
        }
        first = await c.post("/oauth/token", data=data)
        assert first.status_code == 200
        second = await c.post("/oauth/token", data=data)
    assert second.status_code == 400
    assert second.json()["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_token_rejects_bad_pkce_verifier(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    verifier = "ver-" + "x" * 60
    async with client as c:
        client_id, kindred_code = await _full_authorize_and_callback(
            monkeypatch, c, verifier=verifier
        )
        res = await c.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": kindred_code,
                "code_verifier": "completely-different-verifier-of-some-length",
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
            },
        )
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_token_refresh_rotation(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    verifier = "ver-" + "x" * 60
    async with client as c:
        client_id, kindred_code = await _full_authorize_and_callback(
            monkeypatch, c, verifier=verifier
        )
        first = await c.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": kindred_code,
                "code_verifier": verifier,
                "client_id": client_id,
                "redirect_uri": "https://app/cb",
            },
        )
        original_refresh = first.json()["refresh_token"]
        refresh_res = await c.post(
            "/oauth/token",
            data={"grant_type": "refresh_token", "refresh_token": original_refresh},
        )
        assert refresh_res.status_code == 200
        new_body = refresh_res.json()
        assert new_body["access_token"]
        assert new_body["refresh_token"] != original_refresh
        # Original refresh token is now invalid (rotation).
        reuse = await c.post(
            "/oauth/token",
            data={"grant_type": "refresh_token", "refresh_token": original_refresh},
        )
    assert reuse.status_code == 400
    assert reuse.json()["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_token_unsupported_grant_type(client: httpx.AsyncClient) -> None:
    async with client as c:
        res = await c.post("/oauth/token", data={"grant_type": "password"})
    assert res.status_code == 400
    assert res.json()["error"] == "unsupported_grant_type"
