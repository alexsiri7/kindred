---
id: "007"
title: "Web app (journal browser)"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

The MCP interface is invisible to users — they need a dedicated web app to browse entries, review patterns, and manage their account. Without a web UI, the only way to see what Claude has saved is to ask Claude, which is slow and limited.

## What

A React 19 + TypeScript 5.6 + Vite 5.4 single-page app served as a static bundle from the FastAPI backend (port 8001). Twelve pages: Landing (public), Login, AuthCallback, Home (entry list with calendar sidebar), EntryDetail, Patterns (list), PatternDetail (occurrence timeline), Search (semantic search UI), Connect (MCP setup wizard), Settings, McpAuth (OAuth relay), and Privacy. Five backend route groups: `/entries`, `/patterns`, `/search`, `/settings`, `/connect`. State managed by Zustand (auth store + nav badge counts), routing by React Router 7, styling by Tailwind CSS 4, error tracking by Sentry. The FastAPI backend serves the built `dist/` as static files and falls back to `index.html` for all unrecognised paths.
