"""Regression tests for Settings env-var parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from settings import Settings


def test_mcp_allowed_hosts_accepts_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "a.example.com,b.example.com")
    assert Settings().mcp_allowed_hosts == "a.example.com,b.example.com"


def test_mcp_allowed_hosts_accepts_single_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "only.example.com")
    assert Settings().mcp_allowed_hosts == "only.example.com"


def test_mcp_allowed_hosts_default_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.chdir(tmp_path)  # isolate from a developer's local .env
    assert Settings().mcp_allowed_hosts == ""


def test_mcp_allowed_hosts_accepts_bare_hostname_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: pydantic-settings used to JSON-decode list[str] fields,
    which crashed on bare hostnames like 'mcp-production-37d7.up.railway.app'.
    Field is now `str`; instantiation must succeed."""
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp-production-37d7.up.railway.app")
    assert Settings().mcp_allowed_hosts == "mcp-production-37d7.up.railway.app"
