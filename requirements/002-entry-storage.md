---
id: "002"
title: "Journal entry storage"
status: "done"
github_issue: 120
updated: "2026-05-12"
---

## Why

Journaling is only useful if entries are durably stored and privately scoped to each user. Without a purpose-built schema, entries would have no consistent structure and no guarantee of isolation between accounts.

## What

A Supabase-hosted Postgres table `entries` with columns: `id` (uuid pk), `user_id` (uuid, references `auth.users` with CASCADE delete), `date` (date — local user date), `summary` (text), `transcript` (jsonb, optional full conversation), `mood` (freeform text), `created_at`, and `updated_at`. An index on `(user_id, date desc)` keeps list queries fast. Row-Level Security policies ensure each user sees only their own rows. `lib/db.py` provides `insert_entry`, `get_entry_by_id`, `get_entry_by_date`, `list_recent_entries`, and `delete_entry`.
