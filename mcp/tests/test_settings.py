"""Regression tests for Settings env-var parsing."""

from __future__ import annotations

import importlib

import pytest


def test_mcp_allowed_hosts_accepts_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "a.example.com,b.example.com")
    import settings as settings_module

    importlib.reload(settings_module)
    parsed = [
        h.strip()
        for h in settings_module.settings.mcp_allowed_hosts.split(",")
        if h.strip()
    ]
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
