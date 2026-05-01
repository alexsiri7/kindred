"""Smoke tests for each router with auth + supabase clients overridden."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import db
import embeddings
from auth import get_current_user
from main import app

USER_ID = "11111111-2222-3333-4444-555555555555"
USER = {"user_id": USER_ID, "email": "u@example.com", "jwt": "fake-jwt"}


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
    monkeypatch.setattr(db, "user_client", lambda _jwt: _stub_supabase({"entries": rows}))
    res = client.get("/entries")
    assert res.status_code == 200
    assert res.json()[0]["id"] == "e1"


def test_get_entry_returns_404(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(db, "user_client", lambda _jwt: _stub_supabase({"entries": []}))
    res = client.get("/entries/missing")
    assert res.status_code == 404


def test_list_patterns(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    rows = [{"id": "p1", "name": "Sunday dread"}]
    monkeypatch.setattr(db, "user_client", lambda _jwt: _stub_supabase({"patterns": rows}))
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
        db, "user_client", lambda _jwt: _stub_supabase({"__rpc__": matches})
    )
    res = client.get("/search", params={"q": "loneliness"})
    assert res.status_code == 200
    assert res.json()[0]["entry_id"] == "e1"


def test_export_data(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(
        db,
        "user_client",
        lambda _jwt: _stub_supabase(
            {"entries": [{"id": "e1"}], "patterns": [{"id": "p1"}], "pattern_occurrences": []}
        ),
    )
    res = client.get("/export")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == USER_ID
    assert body["entries"][0]["id"] == "e1"


def test_mint_connector_token(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    inserted: dict[str, Any] = {}

    def _service_client() -> MagicMock:
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

    monkeypatch.setattr(db, "service_client", _service_client)
    res = client.post("/connect/token")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["token"], str) and len(body["token"]) > 20
    assert inserted["payload"]["user_id"] == USER_ID
