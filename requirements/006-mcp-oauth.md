---
id: "006"
title: "MCP OAuth 2.1 authentication"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

MCP clients (Claude Desktop, Cursor, Windsurf) need a standard way to obtain delegated access to a user's journal without handling credentials directly. OAuth 2.1 with PKCE is the MCP spec's required auth mechanism, and without it no compliant client can connect.

## What

Six HTTP endpoints in `mcp/oauth.py` implementing OAuth 2.1: RFC 9728 protected-resource metadata (`GET /.well-known/oauth-protected-resource`), RFC 8414 authorization-server metadata (`GET /.well-known/oauth-authorization-server`), RFC 7591 dynamic client registration (`POST /oauth/register`, in-memory registry), authorization endpoint (`GET /oauth/authorize`, PKCE S256 only, redirects to web relay `/mcp-auth`), code-from-session exchange (`POST /oauth/code-from-session`, validates Supabase token, issues Kindred auth code), and token endpoint (`POST /oauth/token`, issues HS256 JWT with 7-day expiry and rotating refresh token with 30-day TTL). Auth codes and sessions expire after 10 minutes. All in-memory state is held in `mcp/oauth_state.py`.
