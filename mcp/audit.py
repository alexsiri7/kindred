"""Configures the ``kindred.audit`` logger and exports an ``audited()`` decorator for MCP tools."""

from __future__ import annotations

import functools
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pythonjsonlogger.json import JsonFormatter

from auth import current_user_id

_audit = logging.getLogger("kindred.audit")
_audit.setLevel(logging.INFO)
# Don't propagate: keeps audit lines out of root handlers (which may add other
# formatters), so each tool call produces exactly one single-line JSON record
# on stdout — what Railway's log pipeline parses.
_audit.propagate = False

if not _audit.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(message)s",
        rename_fields={"asctime": "ts", "levelname": "level"},
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    # UTC timestamps so log records are unambiguous across deploys/regions.
    _formatter.converter = time.gmtime
    _handler.setFormatter(_formatter)
    _audit.addHandler(_handler)


R = TypeVar("R")


def audited(
    tool_name: str,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """Wrap an async MCP tool to emit one structured audit record per invocation."""

    def decorator(fn: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            t0 = time.perf_counter()
            user_id = current_user_id.get(None)
            status = "ok"
            try:
                return await fn(*args, **kwargs)
            except BaseException:
                status = "error"
                raise
            finally:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                _audit.info(
                    "tool_call",
                    extra={
                        "event": "tool_call",
                        "tool": tool_name,
                        "user_id": user_id,
                        "status": status,
                        "duration_ms": duration_ms,
                    },
                )

        return wrapper

    return decorator
