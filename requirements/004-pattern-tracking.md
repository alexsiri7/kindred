---
id: "004"
title: "Recurring pattern tracking (HCB framework)"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Journaling without pattern recognition is just venting. The HCB (Hot Cross Bun) framework from CBT makes recurring cycles visible — "I feel this way, think this, then do that" — so users can notice, name, and eventually interrupt unhelpful patterns. Without structured tracking, patterns stay invisible across sessions.

## What

Two Postgres tables: `patterns` (name unique per user case-insensitively, plus `typical_thoughts`, `typical_emotions`, `typical_behaviors`, `typical_sensations`, denormalized `last_seen_at` and `occurrence_count`) and `pattern_occurrences` (linked to both a pattern and an entry, with per-instance thoughts/emotions/behaviors/sensations, optional `intensity` 1–5, `trigger`, and `notes`). `lib/services/patterns.py` exposes `list_patterns` (filterable by `active_since`), `get_pattern` (by UUID or case-insensitive name), `log_occurrence` (auto-creates the pattern if it doesn't exist, then updates `last_seen_at` and `occurrence_count`), and `list_occurrences`. MCP tools mirror these operations one-to-one.
