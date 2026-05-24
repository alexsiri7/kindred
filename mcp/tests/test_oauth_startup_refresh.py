"""Tests for proactive token refresh on startup (issue #126)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import oauth_state
import settings as settings_module
from oauth import JWT_EXPIRY_SECONDS, REFRESH_TOKEN_TTL_SECONDS, _proactive_refresh

SECRET = "test-secret-do-not-use-in-prod-needs-32-bytes-minimum"
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module.settings, "secret_key", SECRET)


@pytest.fixture(autouse=True)
def _clear_state() -> None:
    oauth_state.refresh_tokens.clear()


def _seed_session(
    token_key: str = "rt-abc",
    user_id: str = USER_ID,
    access_token_age_seconds: int = 0,
    refresh_token_age_seconds: int = 0,
) -> None:
    now = datetime.now(UTC)
    oauth_state.refresh_tokens[token_key] = {
        "user_id": user_id,
        "email": "test@example.com",
        "client_id": "client-1",
        "scope": "mcp",
        "expires_at": now + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS - refresh_token_age_seconds),
        "access_token_issued_at": now - timedelta(seconds=access_token_age_seconds),
    }


def test_no_sessions_is_noop() -> None:
    """Empty refresh_tokens dict: _proactive_refresh must not raise."""
    _proactive_refresh()
    assert oauth_state.refresh_tokens == {}


def test_valid_session_unchanged() -> None:
    """Session with fresh access token: entry is not modified."""
    _seed_session(access_token_age_seconds=60)  # issued 1 minute ago
    _proactive_refresh()
    assert "rt-abc" in oauth_state.refresh_tokens
    entry = oauth_state.refresh_tokens["rt-abc"]
    # access_token_issued_at should NOT have been updated
    age = (datetime.now(UTC) - entry["access_token_issued_at"]).total_seconds()
    assert age >= 60  # still the original timestamp (± small clock skew)


def test_expired_access_token_updates_issued_at() -> None:
    """Session with expired access token: access_token_issued_at is refreshed."""
    expired_age = JWT_EXPIRY_SECONDS + 3600  # 1 hour past expiry
    _seed_session(access_token_age_seconds=expired_age)
    before = datetime.now(UTC)
    _proactive_refresh()
    after = datetime.now(UTC)
    assert "rt-abc" in oauth_state.refresh_tokens
    entry = oauth_state.refresh_tokens["rt-abc"]
    assert before <= entry["access_token_issued_at"] <= after


def test_near_expiry_access_token_is_refreshed() -> None:
    """Session with access token expiring in <5 min: proactively refreshed."""
    # Issued almost JWT_EXPIRY_SECONDS ago (3 min left)
    near_expiry_age = JWT_EXPIRY_SECONDS - 3 * 60
    _seed_session(access_token_age_seconds=near_expiry_age)
    before = datetime.now(UTC)
    _proactive_refresh()
    after = datetime.now(UTC)
    entry = oauth_state.refresh_tokens["rt-abc"]
    assert before <= entry["access_token_issued_at"] <= after


def test_expired_refresh_token_is_dropped() -> None:
    """Session with expired refresh token: entry is removed from memory."""
    oauth_state.refresh_tokens["rt-dead"] = {
        "user_id": USER_ID,
        "email": "test@example.com",
        "client_id": "client-1",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) - timedelta(hours=1),  # expired
        "access_token_issued_at": datetime.now(UTC) - timedelta(days=10),
    }
    _proactive_refresh()
    assert "rt-dead" not in oauth_state.refresh_tokens


def test_expired_refresh_token_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Expired refresh token: a warning with user_id is logged."""
    import logging

    oauth_state.refresh_tokens["rt-dead"] = {
        "user_id": USER_ID,
        "email": None,
        "client_id": "client-1",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) - timedelta(hours=1),
        "access_token_issued_at": datetime.now(UTC) - timedelta(days=10),
    }
    with caplog.at_level(logging.WARNING, logger="oauth"):
        _proactive_refresh()
    assert USER_ID in caplog.text
    assert "re-authenticate" in caplog.text


def test_missing_access_token_issued_at_is_skipped() -> None:
    """Old-format entry without access_token_issued_at: skipped gracefully."""
    oauth_state.refresh_tokens["rt-old"] = {
        "user_id": USER_ID,
        "email": None,
        "client_id": "client-1",
        "scope": "mcp",
        "expires_at": datetime.now(UTC) + timedelta(days=15),
        # No access_token_issued_at
    }
    _proactive_refresh()  # must not raise
    assert "rt-old" in oauth_state.refresh_tokens  # entry preserved
