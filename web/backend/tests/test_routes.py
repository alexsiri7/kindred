"""Smoke tests for each router with auth + supabase clients overridden."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from lib import db, embeddings

from auth import get_current_user
from main import app

USER_ID = "11111111-2222-3333-4444-555555555555"
USER = {
    "user_id": USER_ID,
    "email": "u@example.com",
    "jwt": "fake-jwt",
    "user_metadata": {},
}


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user] = lambda: USER
    yield TestClient(app)
    app.dependency_overrides.clear()


def _stub_table(rows: list[dict[str, Any]]) -> MagicMock:
    """Build a chainable Supabase query stub that always resolves to ``rows``."""
    stub = MagicMock()
    response = MagicMock()
    response.data = rows
    # Every chained method returns the same stub; .execute() yields the response.
    stub.select.return_value = stub
    stub.insert.return_value = stub
    stub.eq.return_value = stub
    stub.order.return_value = stub
    stub.limit.return_value = stub
    stub.gte.return_value = stub
    stub.in_.return_value = stub
    stub.execute.return_value = response
    return stub


def _stub_supabase(table_rows: dict[str, list[dict[str, Any]]]) -> MagicMock:
    sb = MagicMock()
    sb.table = lambda name: _stub_table(table_rows.get(name, []))
    rpc_response = MagicMock()
    rpc_response.data = table_rows.get("__rpc__", [])
    sb.rpc.return_value.execute.return_value = rpc_response
    return sb


def test_list_entries(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    rows = [{"id": "e1", "date": "2026-05-01", "summary": "ok", "mood": None}]
    monkeypatch.setattr(
        db, "user_client", lambda _uid, _jwt=None: _stub_supabase({"entries": rows})
    )
    res = client.get("/entries")
    assert res.status_code == 200
    assert res.json()[0]["id"] == "e1"


def test_get_entry_returns_404(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(
        db, "user_client", lambda _uid, _jwt=None: _stub_supabase({"entries": []})
    )
    res = client.get("/entries/missing")
    assert res.status_code == 404


def test_list_patterns(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    rows = [{"id": "p1", "name": "Sunday dread"}]
    monkeypatch.setattr(
        db, "user_client", lambda _uid, _jwt=None: _stub_supabase({"patterns": rows})
    )
    res = client.get("/patterns")
    assert res.status_code == 200
    assert res.json()[0]["name"] == "Sunday dread"


def test_search_rejects_empty(client: TestClient) -> None:
    res = client.get("/search", params={"q": "   "})
    assert res.status_code == 400


def test_search_returns_matches(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(embeddings, "embed", lambda _t: [0.1, 0.2, 0.3])
    matches = [{"entry_id": "e1", "similarity": 0.9, "content": "x"}]
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _uid, _jwt=None: _stub_supabase({"__rpc__": matches}),
    )
    res = client.get("/search", params={"q": "loneliness"})
    assert res.status_code == 200
    assert res.json()[0]["entry_id"] == "e1"


def test_export_data(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _uid, _jwt=None: _stub_supabase(
            {"entries": [{"id": "e1"}], "patterns": [{"id": "p1"}], "pattern_occurrences": []}
        ),
    )
    res = client.get("/export")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == USER_ID
    assert body["entries"][0]["id"] == "e1"


def test_settings_patch_accepts_crisis_ack(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_update(jwt_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        captured["metadata"] = metadata
        return metadata

    monkeypatch.setattr(db, "update_user_metadata", _fake_update)

    res = client.patch(
        "/settings",
        json={"crisis_disclaimer_acknowledged_at": "2026-05-03T12:00:00Z"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["crisis_disclaimer_acknowledged_at"] == "2026-05-03T12:00:00Z"
    assert captured["metadata"]["crisis_disclaimer_acknowledged_at"] == (
        "2026-05-03T12:00:00Z"
    )


def test_mint_connector_token(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    inserted: dict[str, Any] = {}

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()

        def _table(name: str) -> MagicMock:
            t = MagicMock()
            response = MagicMock()
            response.data = [{"created_at": "2026-05-01T00:00:00Z"}]

            def _insert(payload: dict[str, Any]) -> MagicMock:
                inserted["payload"] = payload
                exec_mock = MagicMock()
                exec_mock.execute.return_value = response
                return exec_mock

            t.insert.side_effect = _insert
            return t

        sb.table.side_effect = _table
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    res = client.post("/connect/token")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["token"], str) and len(body["token"]) > 20
    assert inserted["payload"]["user_id"] == USER_ID


# ---------------------------------------------------------------------------
# settings + account
# ---------------------------------------------------------------------------
def test_get_settings_reads_user_metadata() -> None:
    user = {
        **USER,
        "user_metadata": {"timezone": "America/New_York", "transcript_enabled": False},
    }
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        res = TestClient(app).get("/settings")
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.json() == {
        "timezone": "America/New_York",
        "transcript_enabled": False,
        "crisis_disclaimer_acknowledged_at": None,
    }


def test_get_settings_defaults_when_metadata_empty(client: TestClient) -> None:
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json() == {
        "timezone": None,
        "transcript_enabled": True,
        "crisis_disclaimer_acknowledged_at": None,
    }


def test_patch_settings_invokes_update_user_metadata(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_update(jwt_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        captured["jwt"] = jwt_token
        captured["metadata"] = metadata
        return metadata

    monkeypatch.setattr(db, "update_user_metadata", _fake_update)
    res = client.patch(
        "/settings",
        json={"timezone": "Europe/London", "transcript_enabled": False},
    )
    assert res.status_code == 200
    assert captured["jwt"] == "fake-jwt"
    assert captured["metadata"] == {
        "timezone": "Europe/London",
        "transcript_enabled": False,
    }
    assert res.json() == {
        "timezone": "Europe/London",
        "transcript_enabled": False,
        "crisis_disclaimer_acknowledged_at": None,
    }


def test_delete_account_calls_rpc(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    rpc_calls: list[str] = []

    def _build_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        sb = MagicMock()
        rpc_chain = MagicMock()
        rpc_response = MagicMock()
        rpc_response.data = None
        rpc_chain.execute.return_value = rpc_response

        def _rpc(name: str) -> MagicMock:
            rpc_calls.append(name)
            return rpc_chain

        sb.rpc.side_effect = _rpc
        return sb

    monkeypatch.setattr(db, "user_client", _build_user_client)
    res = client.delete("/account")
    assert res.status_code == 200
    assert res.json() == {"status": "deleted"}
    assert rpc_calls == ["delete_my_account"]


# ---------------------------------------------------------------------------
# get-by-id happy paths (entries + patterns) — locks in the `occurrences`
# attachment that the new lib.services.* helpers add.
# ---------------------------------------------------------------------------
def test_get_entry_returns_200_with_occurrences(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """GET /entries/{id} must include the ``occurrences`` key — frontend contract."""
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _uid, _jwt=None: _stub_supabase(
            {
                "entries": [{"id": "e1", "date": "2026-05-01"}],
                "pattern_occurrences": [{"id": "o1", "entry_id": "e1"}],
            }
        ),
    )
    res = client.get("/entries/e1")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "e1"
    assert body["occurrences"] == [{"id": "o1", "entry_id": "e1"}]


_PATTERN_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_MISSING_UUID = "11111111-1111-1111-1111-111111111111"


def test_get_pattern_returns_200_with_occurrences(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """GET /patterns/{id} must include the ``occurrences`` key — frontend contract."""
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _uid, _jwt=None: _stub_supabase(
            {
                "patterns": [
                    {"id": _PATTERN_UUID, "name": "Sunday dread"}
                ],
                "pattern_occurrences": [
                    {"id": "o1", "pattern_id": _PATTERN_UUID}
                ],
            }
        ),
    )
    res = client.get(f"/patterns/{_PATTERN_UUID}")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Sunday dread"
    assert body["occurrences"] == [{"id": "o1", "pattern_id": _PATTERN_UUID}]


def test_get_pattern_returns_404(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _uid, _jwt=None: _stub_supabase({"patterns": []}),
    )
    res = client.get(f"/patterns/{_MISSING_UUID}")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# JWT propagation — every web route must pass user["jwt"] (web flow), not
# None (MCP flow), to db.user_client. See PR #78 scope item #2.
# ---------------------------------------------------------------------------
def test_routes_propagate_user_jwt_to_user_client(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """Every web route must pass user['jwt'] to db.user_client, or RLS
    silently switches to a server-minted synthetic JWT."""
    received_jwts: list[str | None] = []

    def _spy_user_client(_uid: str, _jwt: str | None = None) -> MagicMock:
        received_jwts.append(_jwt)
        return _stub_supabase(
            {"entries": [], "patterns": [], "pattern_occurrences": []}
        )

    monkeypatch.setattr(db, "user_client", _spy_user_client)
    client.get("/entries")
    client.get("/patterns")
    client.get("/export")

    assert received_jwts, "no calls captured — test setup wrong"
    assert all(j == "fake-jwt" for j in received_jwts), (
        f"some routes dropped the user JWT: {received_jwts}"
    )


# ---------------------------------------------------------------------------
# update_settings GoTrue error translation
# ---------------------------------------------------------------------------
def _gotrue_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("PUT", "https://x.supabase.co/auth/v1/user")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"GoTrue {status_code}", request=request, response=response
    )


def test_patch_settings_translates_gotrue_401(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """A 401 from GoTrue (expired token) must surface as 401, not 500."""

    async def _fake_update(jwt_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        raise _gotrue_status_error(401)

    monkeypatch.setattr(db, "update_user_metadata", _fake_update)
    res = client.patch("/settings", json={"timezone": "UTC"})
    assert res.status_code == 401


def test_patch_settings_translates_gotrue_5xx(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """A 5xx from GoTrue must surface as 502 with no naked 500."""

    async def _fake_update(jwt_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        raise _gotrue_status_error(500)

    monkeypatch.setattr(db, "update_user_metadata", _fake_update)
    res = client.patch("/settings", json={"timezone": "UTC"})
    assert res.status_code == 502


def test_patch_settings_translates_network_error(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """A network/timeout error must surface as 503."""

    async def _fake_update(jwt_token: str, metadata: dict[str, Any]) -> dict[str, Any]:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(db, "update_user_metadata", _fake_update)
    res = client.patch("/settings", json={"timezone": "UTC"})
    assert res.status_code == 503
