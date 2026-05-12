---
id: "010"
title: "Connector setup page"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Connecting an MCP server to Claude Desktop or a code editor requires editing JSON config files and generating auth tokens — steps that are error-prone for non-technical users. A guided setup page removes the guesswork and reduces failed connections.

## What

A three-step wizard at `/connect`: Step 1 displays the MCP base URL with a copy button. Step 2 mints a connector token (32 cryptographically random URL-safe base64 bytes, ~43 chars, 90-day TTL) via `POST /connect/token` and shows it once for copying. Step 3 renders client-specific JSON config snippets for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`), and Windsurf (`~/.codeium/windsurf/mcp_config.json`), each with troubleshooting hints. A one-liner system prompt (`"When connected to Kindred, call the read_guide tool before doing anything else."`) is provided for users to paste into their client's custom instruction field.
