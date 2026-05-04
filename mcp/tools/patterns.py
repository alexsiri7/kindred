"""Pattern-related MCP tools — thin wrappers over lib.services.patterns."""

from __future__ import annotations

import asyncio
from typing import Any

from lib.services import patterns as patterns_service
from mcp.server.fastmcp.exceptions import ToolError

from auth import current_user_id


async def list_patterns(active_since: str | None = None) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    try:
        return await asyncio.to_thread(
            patterns_service.list_patterns, user_id, None, active_since
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc


async def get_pattern(name_or_id: str) -> dict[str, Any]:
    user_id = current_user_id.get()
    try:
        return await asyncio.to_thread(
            patterns_service.get_pattern, user_id, None, name_or_id
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc


async def log_occurrence(
    pattern_name: str,
    entry_id: str,
    thoughts: str,
    emotions: str,
    behaviors: str,
    sensations: str,
    intensity: int | None = None,
    trigger: str | None = None,
    notes: str | None = None,
) -> str:
    user_id = current_user_id.get()
    try:
        return await asyncio.to_thread(
            patterns_service.log_occurrence,
            user_id,
            None,
            pattern_name,
            entry_id,
            thoughts,
            emotions,
            behaviors,
            sensations,
            intensity,
            trigger,
            notes,
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc


async def list_occurrences(
    pattern_name_or_id: str, since: str | None = None
) -> list[dict[str, Any]]:
    user_id = current_user_id.get()
    try:
        return await asyncio.to_thread(
            patterns_service.list_occurrences,
            user_id,
            None,
            pattern_name_or_id,
            since,
        )
    except Exception as exc:
        raise ToolError(str(exc)) from exc
