"""Unit tests for the bounded TTL state stores in oauth_state.py."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

import oauth_state
from oauth_state import (
    StoreFullError,
    cleanup_and_get,
    cleanup_and_pop,
    cleanup_and_store,
)


@pytest.fixture(autouse=True)
def _clear() -> None:
    oauth_state.oauth_sessions.clear()
    oauth_state.auth_codes.clear()
    oauth_state.registered_clients.clear()
    oauth_state.refresh_tokens.clear()


def test_store_and_pop_round_trip() -> None:
    cleanup_and_store(oauth_state.auth_codes, "k", {"user_id": "u"})
    assert cleanup_and_pop(oauth_state.auth_codes, "k") == {"user_id": "u"}
    # Single-use: second pop returns None.
    assert cleanup_and_pop(oauth_state.auth_codes, "k") is None


def test_get_does_not_remove() -> None:
    cleanup_and_store(oauth_state.auth_codes, "k", {"user_id": "u"})
    assert cleanup_and_get(oauth_state.auth_codes, "k") is not None
    assert cleanup_and_get(oauth_state.auth_codes, "k") is not None


def test_expired_datetime_entries_are_evicted_on_get() -> None:
    oauth_state.auth_codes["expired"] = {
        "user_id": "u",
        "expires_at": datetime.now(UTC) - timedelta(seconds=1),
    }
    assert cleanup_and_get(oauth_state.auth_codes, "expired") is None
    assert "expired" not in oauth_state.auth_codes


def test_expired_numeric_entries_are_evicted_on_get() -> None:
    """expires_at as a float (epoch seconds) — the other branch in _is_expired."""
    oauth_state.auth_codes["expired-float"] = {
        "user_id": "u",
        "expires_at": time.time() - 1,
    }
    assert cleanup_and_get(oauth_state.auth_codes, "expired-float") is None


def test_expired_pop_returns_none() -> None:
    oauth_state.auth_codes["expired-pop"] = {
        "user_id": "u",
        "expires_at": datetime.now(UTC) - timedelta(seconds=1),
    }
    assert cleanup_and_pop(oauth_state.auth_codes, "expired-pop") is None


def test_entries_without_expires_at_are_never_evicted() -> None:
    """registered_clients entries don't carry expires_at — they must persist."""
    oauth_state.registered_clients["client-1"] = {"client_id": "client-1"}
    cleanup_and_store(
        oauth_state.registered_clients, "client-2", {"client_id": "client-2"}
    )
    assert "client-1" in oauth_state.registered_clients
    assert "client-2" in oauth_state.registered_clients


def test_store_raises_when_cap_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """StoreFullError must fire — protects against unbounded growth via /oauth/register."""
    monkeypatch.setattr(oauth_state, "MAX_ENTRIES_PER_DICT", 3)
    cleanup_and_store(oauth_state.registered_clients, "a", {"x": 1})
    cleanup_and_store(oauth_state.registered_clients, "b", {"x": 1})
    cleanup_and_store(oauth_state.registered_clients, "c", {"x": 1})
    with pytest.raises(StoreFullError):
        cleanup_and_store(oauth_state.registered_clients, "d", {"x": 1})


def test_store_evicts_then_admits_when_full_of_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After eviction frees space, a new entry must be admitted."""
    monkeypatch.setattr(oauth_state, "MAX_ENTRIES_PER_DICT", 2)
    past = datetime.now(UTC) - timedelta(seconds=1)
    oauth_state.auth_codes["a"] = {"expires_at": past}
    oauth_state.auth_codes["b"] = {"expires_at": past}
    cleanup_and_store(
        oauth_state.auth_codes,
        "c",
        {"expires_at": datetime.now(UTC) + timedelta(minutes=5)},
    )
    assert "c" in oauth_state.auth_codes


def test_lock_serializes_concurrent_writes() -> None:
    """If the lock works, N concurrent writes must produce exactly N entries."""
    n = 200
    keys = [f"k{i}" for i in range(n)]

    def _writer(k: str) -> None:
        cleanup_and_store(oauth_state.auth_codes, k, {"user_id": "u"})

    threads = [threading.Thread(target=_writer, args=(k,)) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(oauth_state.auth_codes) == n
