---
id: "009"
title: "Account settings (export, delete, transcript toggle)"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Users need control over their data — especially sensitive journal content. Without an export option, data is locked in; without a delete option, users can't leave; without a transcript toggle, privacy-conscious users can't opt out of storing raw conversation text.

## What

Four endpoints in `web/backend/routes/settings.py`: `GET /settings` returns `{timezone, transcript_enabled, crisis_disclaimer_acknowledged_at}` from Supabase `user_metadata`; `PATCH /settings` accepts any subset and writes back via the Supabase Admin API; `GET /export` returns a full JSON dump of the user's entries, patterns, and pattern occurrences; `DELETE /account` calls the security-definer Postgres RPC `delete_my_account()` which deletes the `auth.users` row and cascades atomically to all app tables. The Settings web page exposes: timezone autocomplete (populated from `Intl.supportedValuesOf('timeZone')`), transcript toggle, crisis disclaimer acknowledgment, connector token management (list/mint/revoke), one-click JSON export, and account deletion with confirmation.
