"""Tests for the audit decorator: structured log emission per MCP tool call."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
from collections.abc import Iterator

import pytest

import audit
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
    assert isinstance(record.duration_ms, float)  # type: ignore[attr-defined]
    assert record.duration_ms >= 0  # type: ignore[attr-defined]


async def test_audited_emits_record_on_cancellation(
    audit_records: list[logging.LogRecord], _set_user: None
) -> None:
    """Cancelled async tasks must still emit an audit record (status=error) and
    re-raise CancelledError. Locks in the BaseException catch in audit.py — a
    well-meaning narrowing to ``except Exception`` would silently break this."""

    @audited("cancel_tool")
    async def fake() -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await fake()

    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.status == "error"  # type: ignore[attr-defined]
    assert record.tool == "cancel_tool"  # type: ignore[attr-defined]


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


async def test_audit_logger_does_not_propagate_to_root(
    _set_user: None,
) -> None:
    """Behavioural check: a record emitted on kindred.audit must NOT reach
    handlers attached to the root logger. Pinning propagate=False as a contract,
    not just a flag."""
    root = logging.getLogger()
    captured: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = captured.append  # type: ignore[method-assign]
    root.addHandler(handler)
    try:

        @audited("propagate_tool")
        async def fake() -> None:
            return None

        await fake()
    finally:
        root.removeHandler(handler)

    assert captured == [], "audit record leaked to root logger"


def test_audited_preserves_function_signature() -> None:
    async def original_fn(date: str, summary: str) -> str:
        return summary

    wrapped = audited("anything")(original_fn)
    assert wrapped.__name__ == "original_fn"
    # functools.wraps sets __wrapped__ — FastMCP's inspect.signature follows it.
    assert wrapped.__wrapped__ is original_fn  # type: ignore[attr-defined]
    # The actual contract FastMCP relies on: inspect.signature(callable,
    # follow_wrapped=True) reads the original signature to build the JSON
    # schema. Pinning this protects against a regression that swaps
    # functools.wraps for manual __name__ assignment.
    assert inspect.signature(wrapped) == inspect.signature(original_fn)


async def test_audited_emits_single_line_json_with_renamed_fields(
    _set_user: None,
) -> None:
    """End-to-end formatter pipeline: serialise a record through the live
    JsonFormatter and parse it as JSON. Pins the rename_fields contract
    (asctime→ts, levelname→level), the UTC ``Z`` suffix, and the
    one-line-per-call invariant Railway's log pipeline depends on.

    We capture by swapping the production handler's ``stream`` attribute (the
    handler was bound to ``sys.stdout`` at module import, before pytest's
    ``capsys`` could intercept it), so this exercises the *real* configured
    formatter, not a re-instantiated copy.
    """
    import io

    logger = logging.getLogger("kindred.audit")
    assert logger.handlers, "audit logger has no handler — module import failed"
    handler = logger.handlers[0]
    original_stream = handler.stream  # type: ignore[attr-defined]
    buf = io.StringIO()
    handler.stream = buf  # type: ignore[attr-defined]
    try:

        @audited("fmt_tool")
        async def fake() -> None:
            return None

        await fake()
    finally:
        handler.stream = original_stream  # type: ignore[attr-defined]

    out = buf.getvalue().strip()
    assert out, "no audit output captured"
    # Exactly one record per call → exactly one line on stdout.
    assert "\n" not in out, f"audit record must be a single line, got: {out!r}"
    payload = json.loads(out)
    assert set(payload) >= {
        "ts",
        "level",
        "event",
        "tool",
        "user_id",
        "status",
        "duration_ms",
    }
    assert payload["event"] == "tool_call"
    assert payload["tool"] == "fmt_tool"
    assert payload["status"] == "ok"
    assert payload["user_id"] == USER_ID
    # rename_fields contract — silent break if pythonjsonlogger semantics drift.
    assert "asctime" not in payload
    assert "levelname" not in payload
    # UTC marker at end of timestamp (datefmt ends with literal Z).
    assert payload["ts"].endswith("Z"), payload["ts"]


def test_module_reload_does_not_duplicate_handlers() -> None:
    """The ``if not _audit.handlers:`` guard must keep handler count at 1
    across module reloads (uvicorn --reload, test runners) — duplicates
    would emit one audit line per reload generation."""
    logger = logging.getLogger("kindred.audit")
    before = len(logger.handlers)
    try:
        importlib.reload(audit)
        assert len(logger.handlers) == before
        importlib.reload(audit)
        assert len(logger.handlers) == before
    finally:
        # Defensive: trim any duplicates a future regression might leave behind
        # so we don't poison subsequent tests.
        while len(logger.handlers) > before:
            logger.removeHandler(logger.handlers[-1])
