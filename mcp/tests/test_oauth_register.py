"""Dynamic Client Registration tests (RFC 7591)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

import oauth_state
import settings as settings_module
from main import app


@pytest.fixture(autouse=True)
def _set_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )


@pytest.fixture(autouse=True)
def _clear_state() -> None:
    oauth_state.registered_clients.clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_register_returns_201_with_credentials(client: httpx.AsyncClient) -> None:
    res = await client.post(
        "/oauth/register",
        json={
            "client_name": "claude-ai",
            "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "client_id" in data
    assert len(data["client_id"]) == 32  # uuid4().hex
    assert "client_secret" in data
    assert len(data["client_secret"]) >= 32
    assert data["client_name"] == "claude-ai"
    assert data["redirect_uris"] == ["https://claude.ai/api/mcp/auth_callback"]


async def test_register_persists_in_state_store(client: httpx.AsyncClient) -> None:
    res = await client.post(
        "/oauth/register",
        json={"client_name": "x", "redirect_uris": ["https://example.com/cb"]},
    )
    assert res.status_code == 201
    cid = res.json()["client_id"]
    assert cid in oauth_state.registered_clients
    assert oauth_state.registered_clients[cid]["redirect_uris"] == [
        "https://example.com/cb"
    ]


async def test_register_assigns_distinct_client_ids(client: httpx.AsyncClient) -> None:
    body = {"client_name": "same", "redirect_uris": ["https://a/cb"]}
    r1 = await client.post("/oauth/register", json=body)
    r2 = await client.post("/oauth/register", json=body)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["client_id"] != r2.json()["client_id"]


async def test_register_supplies_defaults_for_omitted_fields(
    client: httpx.AsyncClient,
) -> None:
    res = await client.post("/oauth/register", json={})
    assert res.status_code == 201
    data = res.json()
    assert data["grant_types"] == ["authorization_code"]
    assert data["response_types"] == ["code"]
    assert data["scope"] == "mcp"


async def test_register_rejects_non_list_redirect_uris(
    client: httpx.AsyncClient,
) -> None:
    """RFC 7591 specifies redirect_uris as a JSON array of strings.

    Without this validation, the in-membership check at /oauth/authorize
    degrades to substring matching and an attacker can craft a redirect_uri
    that's a substring of the registered string.
    """
    res = await client.post(
        "/oauth/register",
        json={"redirect_uris": "https://app.example.com/cb"},
    )
    assert res.status_code == 400


async def test_register_rejects_non_string_redirect_uri_elements(
    client: httpx.AsyncClient,
) -> None:
    res = await client.post(
        "/oauth/register",
        json={"redirect_uris": ["https://ok/cb", 123]},
    )
    assert res.status_code == 400


async def test_register_with_malformed_json_uses_defaults(
    client: httpx.AsyncClient,
) -> None:
    res = await client.post(
        "/oauth/register",
        content=b"not-valid-json{{{",
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 201
    assert res.json()["scope"] == "mcp"


async def test_register_with_array_body_uses_defaults(
    client: httpx.AsyncClient,
) -> None:
    res = await client.post("/oauth/register", json=[1, 2, 3])
    assert res.status_code == 201
    assert res.json()["grant_types"] == ["authorization_code"]
