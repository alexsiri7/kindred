"""Discovery endpoint tests (RFC 9728 + RFC 8414)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

import settings as settings_module
from main import app

BASE = "https://test.example.com"


@pytest.fixture(autouse=True)
def _set_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", BASE)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_protected_resource_metadata(client: httpx.AsyncClient) -> None:
    res = await client.get("/.well-known/oauth-protected-resource")
    assert res.status_code == 200
    data = res.json()
    assert data["resource"] == f"{BASE}/mcp/"
    assert data["authorization_servers"] == [BASE]
    assert data["scopes_supported"] == ["mcp"]


async def test_authorization_server_metadata(client: httpx.AsyncClient) -> None:
    res = await client.get("/.well-known/oauth-authorization-server")
    assert res.status_code == 200
    data = res.json()
    assert data["issuer"] == BASE
    assert data["authorization_endpoint"] == f"{BASE}/oauth/authorize"
    assert data["token_endpoint"] == f"{BASE}/oauth/token"
    assert data["registration_endpoint"] == f"{BASE}/oauth/register"
    assert data["response_types_supported"] == ["code"]
    assert data["grant_types_supported"] == ["authorization_code", "refresh_token"]
    assert data["code_challenge_methods_supported"] == ["S256"]
    assert data["scopes_supported"] == ["mcp"]


async def test_protected_resource_metadata_501_when_base_url_unset(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", "")
    res = await client.get("/.well-known/oauth-protected-resource")
    assert res.status_code == 501


async def test_authorization_server_metadata_501_when_base_url_unset(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_base_url", "")
    res = await client.get("/.well-known/oauth-authorization-server")
    assert res.status_code == 501
