---
id: "005"
title: "MCP prompts (/kindred-start and guide resource)"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Without explicit guidance, an AI assistant defaults to problem-solving and advice-giving — the opposite of good emotional support. A surfaced guide ensures Claude adopts the right therapeutic stance (be with → listen → validate → HCB) before touching any journaling tools, so the experience feels supportive rather than transactional.

## What

A `kindred://guide` MCP resource registered in `mcp/main.py` that reads `prompts/kindred-guide.md` fresh from disk on every access, ensuring the guide can be updated without redeployment. A `read_guide` tool exposes the same content for clients that prefer tool calls. A `GUIDE_NUDGE` string is appended to every other tool's `.description` field to continuously remind the assistant to consult the guide. The guide covers: grounding the session in time, following the feeling thread over the story thread, walking through HCB quadrants when a moment stands out, matching to existing patterns, and closing by confirming summary + mood before calling `save_entry`.
