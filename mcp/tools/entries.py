"""Entry-related MCP tools — thin wrappers over lib.services.entries."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from lib.services import entries as entries_service
from mcp.server.fastmcp.exceptions import ToolError

from auth import current_user_id


async def _call(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except Exception as exc:
        raise ToolError(str(exc)) from exc


async def save_entry(
    date: str,
    summary: str,
    mood: str | None = None,
    transcript: list[dict[str, str]] | None = None,
) -> str:
    """Persist a journaling session and embed its summary.

    Same-day re-entry: PRD §Open questions calls "append" the default but
    defers it as out of scope. Today's implementation creates a separate row
    per call — same-day callers will produce two rows.
    """
    user_id = current_user_id.get()
    return await _call(entries_service.save_entry, user_id, None, date, summary, mood, transcript)


async def get_entry(
    date: str | None = None,
    id: str | None = None,
) -> dict[str, Any]:
    user_id = current_user_id.get()
    return await _call(
        entries_service.get_entry_by_date_or_id, user_id, None, date=date, entry_id=id
    )


async def list_recent_entries(limit: int = 10) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    return await _call(entries_service.list_recent_entries, user_id, None, limit)


async def search_entries(query: str, limit: int = 5) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    return await _call(entries_service.search_entries, user_id, None, query, limit)
