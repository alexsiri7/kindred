"""Regression tests for Settings env-var parsing."""

from __future__ import annotations

import importlib

import pytest


def test_mcp_allowed_hosts_accepts_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "a.example.com,b.example.com")
    import settings as settings_module

    importlib.reload(settings_module)
    parsed = [h.strip() for h in settings_module.settings.mcp_allowed_hosts.split(",") if h.strip()]
    assert parsed == ["a.example.com", "b.example.com"]


def test_mcp_allowed_hosts_accepts_single_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "only.example.com")
    import settings as settings_module

    importlib.reload(settings_module)
    assert settings_module.settings.mcp_allowed_hosts == "only.example.com"


def test_mcp_allowed_hosts_default_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    import settings as settings_module

    importlib.reload(settings_module)
    assert settings_module.settings.mcp_allowed_hosts == ""


@pytest.mark.parametrize(
    ("env_var", "field"),
    [
        ("MCP_BASE_URL", "mcp_base_url"),
        ("SECRET_KEY", "secret_key"),
        ("SUPABASE_ANON_KEY", "supabase_anon_key"),
        ("SUPABASE_JWT_SECRET", "supabase_jwt_secret"),
    ],
)
def test_oauth_settings_round_trip(
    monkeypatch: pytest.MonkeyPatch, env_var: str, field: str
) -> None:
    monkeypatch.setenv(env_var, f"value-for-{field}")
    import settings as settings_module

    importlib.reload(settings_module)
    assert getattr(settings_module.settings, field) == f"value-for-{field}"


@pytest.mark.parametrize(
    "field",
    ["mcp_base_url", "secret_key", "supabase_anon_key", "supabase_jwt_secret"],
)
def test_oauth_settings_default_empty(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    for env_var in (
        "MCP_BASE_URL",
        "SECRET_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_JWT_SECRET",
    ):
        monkeypatch.delenv(env_var, raising=False)
    import settings as settings_module

    importlib.reload(settings_module)
    assert getattr(settings_module.settings, field) == ""
