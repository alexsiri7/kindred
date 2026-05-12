---
id: "008"
title: "Google OAuth authentication (web)"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Users should sign in with an identity they already trust — not a new password. Google OAuth via Supabase removes the credential-management burden and instantly narrows the user pool to Google account holders, reducing spam and simplifying onboarding.

## What

Supabase handles the full Google OAuth dance. The Login page calls `supabase.auth.signInWithOAuth({provider: 'google'})` with a `redirectTo` pointing to `/auth/callback`. AuthCallback.tsx receives the session, which the Supabase JS client stores automatically. Every authenticated backend request passes through the `get_current_user()` FastAPI dependency, which extracts the Bearer token, fetches the JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`, and verifies the ES256 signature. Postgres Row-Level Security resolves `auth.uid()` from the same JWT to scope all database queries to the authenticated user.
