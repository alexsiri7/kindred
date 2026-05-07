from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError


async def _call[T](fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except Exception as exc:
        raise ToolError(str(exc)) from exc
