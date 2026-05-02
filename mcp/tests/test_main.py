"""Tests for transport-security helpers in main.py."""

from __future__ import annotations

import pytest

from main import _build_transport_security, _parse_allowed_hosts


def test_parse_allowed_hosts_csv() -> None:
    assert _parse_allowed_hosts("a.example.com,b.example.com") == [
        "a.example.com",
        "b.example.com",
    ]


def test_parse_allowed_hosts_single_value() -> None:
    assert _parse_allowed_hosts("only.example.com") == ["only.example.com"]


def test_parse_allowed_hosts_empty_returns_empty_list() -> None:
    assert _parse_allowed_hosts("") == []


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("a.example.com, b.example.com", ["a.example.com", "b.example.com"]),
        (" only.example.com ", ["only.example.com"]),
        (",a.example.com,", ["a.example.com"]),
        (" , , ", []),
    ],
)
def test_parse_allowed_hosts_handles_whitespace_and_empties(raw: str, expected: list[str]) -> None:
    assert _parse_allowed_hosts(raw) == expected


def test_build_transport_security_disabled_when_no_hosts() -> None:
    ts = _build_transport_security("")
    assert ts.enable_dns_rebinding_protection is False


def test_build_transport_security_disabled_when_only_whitespace() -> None:
    ts = _build_transport_security(" , , ")
    assert ts.enable_dns_rebinding_protection is False


def test_build_transport_security_enabled_with_single_host() -> None:
    ts = _build_transport_security("mcp-production-37d7.up.railway.app")
    assert ts.enable_dns_rebinding_protection is True
    assert ts.allowed_hosts == ["mcp-production-37d7.up.railway.app"]


def test_build_transport_security_enabled_with_csv_hosts() -> None:
    ts = _build_transport_security("a.example.com, b.example.com")
    assert ts.enable_dns_rebinding_protection is True
    assert ts.allowed_hosts == ["a.example.com", "b.example.com"]
