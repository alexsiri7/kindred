"""Tests for the audit decorator: structured log emission per MCP tool call."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from audit import audited
from auth import current_user_id

USER_ID = "00000000-1111-2222-3333-444444444444"


@pytest.fixture
def audit_records() -> Iterator[list[logging.LogRecord]]:
    """Capture records emitted to the kindred.audit logger.

    Needed because the audit logger has propagate=False, so pytest's caplog
    (which attaches to the root logger) won't see them by default.
    """
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    logger = logging.getLogger("kindred.audit")
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


@pytest.fixture
def _set_user() -> Iterator[None]:
    token = current_user_id.set(USER_ID)
    try:
        yield
    finally:
        current_user_id.reset(token)


async def test_audited_emits_one_record_on_success(
    audit_records: list[logging.LogRecord], _set_user: None
) -> None:
    @audited("dummy_tool")
    async def fake(x: int) -> int:
        return x * 2

    result = await fake(21)

    assert result == 42
    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.message == "tool_call"
    assert record.event == "tool_call"  # type: ignore[attr-defined]
    assert record.tool == "dummy_tool"  # type: ignore[attr-defined]
    assert record.user_id == USER_ID  # type: ignore[attr-defined]
    assert record.status == "ok"  # type: ignore[attr-defined]
    assert isinstance(record.duration_ms, float)  # type: ignore[attr-defined]
    assert record.duration_ms >= 0  # type: ignore[attr-defined]


async def test_audited_emits_error_status_on_exception(
    audit_records: list[logging.LogRecord], _set_user: None
) -> None:
    @audited("boom_tool")
    async def fake() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await fake()

    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.status == "error"  # type: ignore[attr-defined]
    assert record.tool == "boom_tool"  # type: ignore[attr-defined]


async def test_audited_uses_none_user_id_when_contextvar_unset(
    audit_records: list[logging.LogRecord],
) -> None:
    # Intentionally do NOT use _set_user — current_user_id is unset.
    @audited("no_user_tool")
    async def fake() -> str:
        return "ok"

    result = await fake()

    assert result == "ok"
    assert len(audit_records) == 1
    assert audit_records[0].user_id is None  # type: ignore[attr-defined]


def test_audit_logger_does_not_propagate() -> None:
    assert logging.getLogger("kindred.audit").propagate is False


def test_audited_preserves_function_name() -> None:
    async def original_fn() -> None:
        return None

    wrapped = audited("anything")(original_fn)
    assert wrapped.__name__ == "original_fn"
    # functools.wraps sets __wrapped__ — FastMCP's inspect.signature follows it.
    assert wrapped.__wrapped__ is original_fn  # type: ignore[attr-defined]
