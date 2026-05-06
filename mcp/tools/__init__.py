"""Shared helpers for MCP tool modules."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError


def to_tool_error[R](
    fn: Callable[..., Awaitable[R]],
) -> Callable[..., Awaitable[R]]:
    """Surface service-layer exceptions to the agent as ``ToolError``.

    Without this, FastMCP swallows raised exceptions and returns a generic
    "Error executing tool" message — the agent has no signal to retry or
    correct its arguments. ``ToolError`` is the protocol-level escape hatch
    that lets the original message reach the agent (issue #79).
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> R:
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            raise ToolError(str(exc)) from exc

    return wrapper
