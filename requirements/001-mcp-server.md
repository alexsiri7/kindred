---
id: "001"
title: "MCP server with journaling tools"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Claude and other AI assistants need structured tools to read and write a user's journal. Without an MCP server exposing journaling operations, the assistant has no way to persist sessions, recall history, or track recurring patterns — making each conversation stateless and disconnected from the user's emotional arc.

## What

A FastMCP server deployed on Railway at `kindred.interstellarai.net/mcp` exposing nine tools: `save_entry` (persist a session with summary, mood, and optional transcript), `get_entry` (fetch by date or UUID), `list_recent_entries` (paginated history), `search_entries` (semantic search), `list_patterns` (active HCB cycles), `get_pattern` (single pattern with quadrants), `log_occurrence` (record a pattern instance against an entry), `list_occurrences` (occurrence timeline), and `read_guide` (fetch the Kindred usage guide). All tools carry `@audited()` structured-logging and are wrapped in `asyncio.to_thread()` for async compatibility. Rate-limiting middleware is applied globally.
