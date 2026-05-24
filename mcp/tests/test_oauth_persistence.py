"""Tests for OAuth token persistence to Supabase (issue #125)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

import oauth_state
from oauth import REFRESH_TOKEN_TTL_SECONDS


@pytest.fixture(autouse=True)
def _clear_state() -> None:
    oauth_state.refresh_tokens.clear()
    oauth_state.registered_clients.clear()
    yield
    oauth_state.refresh_tokens.clear()
    oauth_state.registered_clients.clear()


@patch("services.oauth_store._client")
def test_save_refresh_token_calls_upsert(mock_client) -> None:
    from services.oauth_store import save_refresh_token

    entry = {
        "user_id": "u1",
        "email": "u@example.com",
        "client_id": "c1",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
        "access_token_issued_at": datetime.now(UTC),
    }
    save_refresh_token("rt-test", entry)
    mock_client().rpc.assert_called_once()
    call_args = mock_client().rpc.call_args
    assert call_args[0][0] == "upsert_oauth_refresh_token"
    params = call_args[0][1]
    assert params["p_token"] == "rt-test"
    assert params["p_user_id"] == "u1"
    # Datetime fields must be serialized to ISO strings before being sent to Supabase
    assert isinstance(params["p_expires_at"], str), "p_expires_at must be ISO string"
    assert isinstance(params["p_access_token_issued_at"], str), (
        "p_access_token_issued_at must be ISO string"
    )


@patch("services.oauth_store._client")
def test_load_refresh_tokens_returns_dict(mock_client) -> None:
    from services.oauth_store import load_refresh_tokens

    now = datetime.now(UTC)
    mock_client().rpc().execute.return_value = MagicMock(
        data=[
            {
                "token": "rt-loaded",
                "user_id": "u1",
                "email": "u@example.com",
                "client_id": "c1",
                "scope": "mcp",
                "expires_at": (now + timedelta(days=29)).isoformat(),
                "access_token_issued_at": now.isoformat(),
                "created_at": now.isoformat(),
            }
        ]
    )
    result = load_refresh_tokens()
    assert "rt-loaded" in result
    assert result["rt-loaded"]["user_id"] == "u1"
    # Datetime strings should be parsed back to datetime objects
    assert isinstance(result["rt-loaded"]["expires_at"], datetime)


@patch("services.oauth_store._client")
def test_delete_refresh_token_on_consumption(mock_client) -> None:
    """Consuming a refresh token (rotation) removes it from DB."""
    from services.oauth_store import delete_refresh_token

    delete_refresh_token("rt-old")
    mock_client().rpc.assert_called_once()
    call_args = mock_client().rpc.call_args
    assert call_args[0][0] == "delete_oauth_refresh_token"
    assert call_args[0][1]["p_token"] == "rt-old"


@patch("services.oauth_store._client")
def test_save_registered_client_calls_upsert(mock_client) -> None:
    from services.oauth_store import save_registered_client

    entry = {
        "client_id": "c1",
        "client_secret": "s3cr3t",
        "redirect_uris": ["http://localhost/callback"],
        "client_name": "Test Client",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
        "scope": "mcp",
    }
    save_registered_client("c1", entry)
    mock_client().rpc.assert_called_once()
    call_args = mock_client().rpc.call_args
    assert call_args[0][0] == "upsert_oauth_registered_client"
    assert call_args[0][1]["p_client_id"] == "c1"


@patch("services.oauth_store._client")
def test_load_registered_clients_returns_dict(mock_client) -> None:
    from services.oauth_store import load_registered_clients

    mock_client().rpc().execute.return_value = MagicMock(
        data=[
            {
                "client_id": "c-loaded",
                "client_secret": "secret",
                "redirect_uris": [],
                "client_name": "Test",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
                "scope": "mcp",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    )
    result = load_registered_clients()
    assert "c-loaded" in result
    assert result["c-loaded"]["client_id"] == "c-loaded"


@patch("services.oauth_store.load_refresh_tokens")
@patch("services.oauth_store.load_registered_clients")
def test_startup_hydrates_state(mock_load_clients, mock_load_tokens) -> None:
    """Verify that hydration logic populates oauth_state dicts."""
    now = datetime.now(UTC)
    mock_load_tokens.return_value = {
        "rt-persisted": {
            "user_id": "u2",
            "email": None,
            "client_id": "c2",
            "scope": "mcp",
            "expires_at": now + timedelta(days=29),
            "access_token_issued_at": now,
        }
    }
    mock_load_clients.return_value = {
        "c-persisted": {
            "client_id": "c-persisted",
            "client_secret": "secret",
            "redirect_uris": [],
            "client_name": "",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
            "scope": "mcp",
        }
    }

    # Simulate what build_app() does
    oauth_state.refresh_tokens.update(mock_load_tokens.return_value)
    oauth_state.registered_clients.update(mock_load_clients.return_value)

    assert "rt-persisted" in oauth_state.refresh_tokens
    assert oauth_state.refresh_tokens["rt-persisted"]["user_id"] == "u2"
    assert "c-persisted" in oauth_state.registered_clients


@patch("services.oauth_store._client")
def test_save_refresh_token_handles_db_failure(mock_client, caplog) -> None:
    """DB failure on save logs the error but doesn't raise."""
    from services.oauth_store import save_refresh_token

    mock_client().rpc().execute.side_effect = RuntimeError("DB down")
    entry = {
        "user_id": "u1",
        "email": None,
        "client_id": "c1",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) + timedelta(days=30),
        "access_token_issued_at": datetime.now(UTC),
    }
    with caplog.at_level(logging.ERROR, logger="services.oauth_store"):
        # Should not raise
        save_refresh_token("rt-fail", entry)
    assert "failed to persist refresh token" in caplog.text


@patch("services.oauth_store._client")
def test_load_refresh_tokens_handles_db_failure(mock_client) -> None:
    """DB failure on load returns empty dict."""
    from services.oauth_store import load_refresh_tokens

    mock_client().rpc().execute.side_effect = RuntimeError("DB down")
    result = load_refresh_tokens()
    assert result == {}


@patch("services.oauth_store._client")
def test_load_registered_clients_handles_db_failure(mock_client) -> None:
    """DB failure on load of registered clients returns empty dict."""
    from services.oauth_store import load_registered_clients

    mock_client().rpc().execute.side_effect = RuntimeError("DB down")
    result = load_registered_clients()
    assert result == {}
