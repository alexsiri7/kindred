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
    """Stub embeddings + db so search_entries and list_recent_entries
    tool bodies succeed without external dependencies."""
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
        # /oauth/* prefix must also bypass; FastMCP's handler may 4xx the
        # body, but the rate-limit layer must not 429 it.
        for _ in range(20):
            r = await c.post(
                "/oauth/register",
                json={"client_name": "test", "redirect_uris": ["http://x"]},
            )
            assert r.status_code != 429


@pytest.mark.asyncio
async def test_unauthenticated_returns_401_not_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)
    monkeypatch.setattr(
        settings_module.settings, "mcp_base_url", "https://test.example.com"
    )

    import main as main_module

    async def reject(_token: str) -> str | None:
        return None

    monkeypatch.setattr(main_module, "resolve_user_id", reject)
    monkeypatch.setattr(main_module, "resolve_user_id_from_jwt", lambda _t: None)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        statuses = []
        for _ in range(5):
            r = await c.post("/mcp/", headers={"authorization": "Bearer bogus"})
            statuses.append(r.status_code)

    # Every single one must be 401 — no request may sneak past as 429.
    assert statuses == [401, 401, 401, 401, 401]


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


# ---------------------------------------------------------------------------
# Logging hygiene (privacy boundary on the 429 INFO log)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_log_does_not_leak_body(
    monkeypatch: pytest.MonkeyPatch,
    _stub_auth: None,
    _stub_search_tool: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The 429 INFO log records user prefix + bucket + retry_after only.

    Privacy boundary: JSON-RPC body and tool arguments must NOT appear in
    any log record (Review Focus Area #4 in scope.md).
    """
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1000)
    monkeypatch.setattr(
        settings_module.settings, "mcp_rate_limit_per_tool", "search_entries:1"
    )
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    secret_query = "deeply-personal-journal-content-DO-NOT-LOG"
    from main import app

    with caplog.at_level("INFO", logger="main"):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            headers = {"authorization": f"Bearer {BEARER}"}
            await c.post(
                "/mcp/",
                json=_tools_call("search_entries", query=secret_query),
                headers=headers,
            )
            denied = await c.post(
                "/mcp/",
                json=_tools_call("search_entries", query=secret_query),
                headers=headers,
            )
            assert denied.status_code == 429

    rl_records = [r for r in caplog.records if "rate_limited" in r.getMessage()]
    assert len(rl_records) == 1, "expected exactly one 429 INFO log"
    msg = rl_records[0].getMessage()
    # Format contract.
    assert msg.startswith(f"rate_limited user={USER_ID[:8]} ")
    assert "bucket=search_entries" in msg
    assert "retry_after=" in msg
    # Privacy contract: body / args / full user id must not leak anywhere.
    full_text = "\n".join(r.getMessage() for r in caplog.records)
    assert secret_query not in full_text
    assert USER_ID not in full_text  # only the 8-char prefix
    assert "arguments" not in full_text
    assert "jsonrpc" not in full_text


# ---------------------------------------------------------------------------
# JSON-RPC body parsing edge cases (non-tools/call methods, malformed bodies)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_tools_call_methods_do_not_crash(
    monkeypatch: pytest.MonkeyPatch, _stub_auth: None
) -> None:
    """initialize / tools/list / empty / non-JSON bodies must not 500
    in the rate-limit middleware. FastMCP downstream may still 4xx them."""
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_global_per_min", 1000)
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_per_tool", "")
    monkeypatch.setattr(settings_module.settings, "mcp_rate_limit_disabled", False)

    from main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        headers = {"authorization": f"Bearer {BEARER}"}
        # Non-JSON body.
        r1 = await c.post("/mcp/", content=b"not-json-at-all", headers=headers)
        assert r1.status_code != 500
        # Valid JSON but wrong shape (list, not dict).
        r2 = await c.post("/mcp/", json=["nope"], headers=headers)
        assert r2.status_code != 500
        # Empty body.
        r3 = await c.post("/mcp/", content=b"", headers=headers)
        assert r3.status_code != 500
        # Valid JSON-RPC but a different method (initialize is the FIRST
        # request every MCP client sends).
        r4 = await c.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers=headers,
        )
        assert r4.status_code != 500
        # tools/list — no params.name; must hit only the global bucket.
        r5 = await c.post(
            "/mcp/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=headers,
        )
        assert r5.status_code != 500


# ---------------------------------------------------------------------------
# Multi-chunk body buffering (uvicorn may chunk large request bodies; the
# httpx.ASGITransport-driven tests above always send a single chunk.)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_rate_limit_buffers_multi_chunk_body() -> None:
    """Body chunks split across multiple http.request events are reassembled."""
    from auth import current_user_id
    from main import with_rate_limit
    from rate_limit import RateLimiter

    chunks = [
        b'{"jsonrpc":"2.0","id":1,"method":"tools/call",',
        b'"params":{"name":"search_entries","arguments":{"query":"hi"}}}',
    ]
    received_body = bytearray()

    async def inner_app(scope: Any, receive: Any, send: Any) -> None:
        # Drain everything the middleware replayed.
        while True:
            msg = await receive()
            if msg.get("type") != "http.request":
                break
            received_body.extend(msg.get("body", b""))
            if not msg.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    limiter = RateLimiter(global_per_min=10, per_tool={}, disabled=False)
    app = with_rate_limit(inner_app, limiter=limiter)

    queue: list[dict[str, Any]] = [
        {"type": "http.request", "body": chunks[0], "more_body": True},
        {"type": "http.request", "body": chunks[1], "more_body": False},
    ]

    async def fake_receive() -> dict[str, Any]:
        return queue.pop(0)

    sent: list[dict[str, Any]] = []

    async def fake_send(msg: dict[str, Any]) -> None:
        sent.append(msg)

    token = current_user_id.set("user-x")
    try:
        await app(
            {"type": "http", "path": "/mcp/", "headers": []},
            fake_receive,
            fake_send,
        )
    finally:
        current_user_id.reset(token)

    assert bytes(received_body) == chunks[0] + chunks[1]
    assert sent[0]["status"] == 200
