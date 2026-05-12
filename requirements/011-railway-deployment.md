---
id: "011"
title: "Two-service Railway deployment"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

The MCP server and the web backend have different uptime and scaling needs, and keeping them as one deployable would couple unrelated failure domains. Splitting into two Railway services lets each be restarted, scaled, or updated independently while sharing one Supabase project and one `lib/` Python package.

## What

Two services in the same Railway project: the MCP service runs `mcp/Dockerfile` (base: `python:3.12-slim`, copies `lib/` and `mcp/` and `prompts/`, exposes port 8000, health-checked at `/healthz`); the Web service runs `web/Dockerfile` in two stages (stage 1: `node:20-slim` builds the React bundle with Vite build args `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`, `VITE_SENTRY_DSN`; stage 2: `python:3.12-slim` copies `lib/`, the backend, and the built static bundle, exposes port 8001). Both Dockerfiles are built from the repo root so `COPY lib/` resolves correctly. CI builds both Dockerfiles on every PR as a drift gate, and `railway up` runs on merge to main using `RAILWAY_TOKEN` from GitHub Actions secrets.
