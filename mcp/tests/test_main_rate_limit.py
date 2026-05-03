"""Integration tests for the rate-limit ASGI middleware (#42).

Each test resets the cached default limiter and patches settings before
sending requests through ``main.app`` via httpx.ASGITransport.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

import db
import embeddings
import rate_limit
import settings as settings_module

USER_ID = "00000000-1111-2222-3333-444444444444"
BEARER = "fake-connector-token"


@pytest.fixture(autouse=True)
def _reset_limiter() -> Any:
    rate_limit.reset_for_tests()
    yield
    rate_limit.reset_for_tests()


@pytest.fixture
def _stub_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any non-empty bearer token resolve to USER_ID."""

    async def fake_resolve(token: str) -> str | None:
        return USER_ID if token else None

    # main imported these symbols by name, so patch on `main`.
    import main as main_module

    monkeypatch.setattr(main_module, "resolve_user_id", fake_resolve)
    monkeypatch.setattr(main_module, "resolve_user_id_from_jwt", lambda token: None)


@pytest.fixture
def _stub_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make search_entries tool body succeed without hitting embeddings/db."""
    monkeypatch.setattr(embeddings, "embed", lambda text: [0.0, 0.1, 0.2])
    monkeypatch.setattr(
        db, "match_entries", lambda user_id, vector, limit: []
    )
    monkeypatch.setattr(
        db, "list_recent_entries", lambda user_id, limit: []
    )


def _tools_call(name: str, **arguments: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


# ---------------------------------------------------------------------------
# Global limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_limit_breach_returns_429_with_retry_after(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None, _stub_search_tool: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 2)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        responses = []
        for _ in range(3):
            r = await c.post(
                "/mcp/",
                json=_tools_call("list_recent_entries", limit=1),
                headers=headers,
            )
            responses.append(r)

    assert responses[2].status_code == 429
    retry_after = responses[2].headers.get("retry-after")
    assert retry_after is not None
    assert int(retry_after) >= 1
    body = responses[2].json()
    assert body["error"] == "rate_limited"
    assert body["retry_after"] == int(retry_after)


# ---------------------------------------------------------------------------
# Per-tool limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_entries_per_tool_limit(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None, _stub_search_tool: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1000)
    monkeypatch.setattr(
        settings_module.settings, "mcp_rate_limit_per_tool", "search_entries:1"
    )
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        first = await c.post(
            "/mcp/", json=_tools_call("search_entries", query="x"), headers=headers
        )
        second = await c.post(
            "/mcp/", json=_tools_call("search_entries", query="y"), headers=headers
        )

    assert first.status_code != 429
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) >= 1


@pytest.mark.asyncio
async def test_other_tool_unaffected_by_search_limit(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None, _stub_search_tool: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1000)
    monkeypatch.setattr(
        settings_module.settings, "mcp_rate_limit_per_tool", "search_entries:1"
    )
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        await c.post("/mcp/", json=_tools_call("search_entries", query="x"), headers=headers)
        denied = await c.post(
            "/mcp/", json=_tools_call("search_entries", query="y"), headers=headers
        )
        other = await c.post(
            "/mcp/",
            json=_tools_call("list_recent_entries", limit=1),
            headers=headers,
        )

    assert denied.status_code == 429
    assert other.status_code != 429


# ---------------------------------------------------------------------------
# Disable kill-switch and bypass paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disabled_flag_bypasses_limit(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None, _stub_search_tool: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", True)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        for _ in range(10):
            r = await c.post(
                "/mcp/",
                json=_tools_call("list_recent_entries", limit=1),
                headers=headers,
            )
            assert r.status_code != 429


@pytest.mark.asyncio
async def test_public_paths_not_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(20):
            r = await c.get("/.well-known/oauth-protected-resource")
            assert r.status_code != 429


@pytest.mark.asyncio
async def test_unauthenticated_returns_401_not_429(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )

    # Override _stub_auth to make every token fail to resolve.
    import main as main_module

    async def reject(_token: str) -> str | None:
        return None

    monkeypatch.setattr(main_module, "resolve_user_id", reject)
    monkeypatch.setattr(main_module, "resolve_user_id_from_jwt", lambda _t: None)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        for _ in range(5):
            r = await c.post("/mcp/", headers={"authorization": "Bearer bogus"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Window reset via clock manipulation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_window_reset_via_monkeypatched_clock(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None, _stub_search_tool: None
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    box = [1_000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: box[0])

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        first = await c.post(
            "/mcp/", json=_tools_call("list_recent_entries", limit=1), headers=headers
        )
        second = await c.post(
            "/mcp/", json=_tools_call("list_recent_entries", limit=1), headers=headers
        )
        # Advance past the window.
        box[0] += 61.0
        third = await c.post(
            "/mcp/", json=_tools_call("list_recent_entries", limit=1), headers=headers
        )

    assert first.status_code != 429
    assert second.status_code == 429
    assert third.status_code != 429
