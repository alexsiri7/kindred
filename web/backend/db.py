"""Supabase client factory + GoTrue self-service helpers.

Routes use ``user_client(jwt)`` so RLS scopes every query to the caller.
Privileged operations (account deletion, connector-token mints) intentionally
do NOT live in this module — they run through RLS policies and security-
definer Postgres functions, see ``supabase/migrations/002_*.sql``.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
from supabase import Client, create_client

from settings import settings


def user_client(user_jwt: str) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(user_jwt)
    return client


async def update_user_metadata(jwt: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Self-service metadata update via GoTrue's PUT /auth/v1/user.

    GoTrue's user-side endpoint expects ``{"data": {...}}`` (NOT
    ``{"user_metadata": {...}}``). Returns the merged ``user_metadata`` from
    the response so callers get the persisted state, not a local copy.
    """
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.put(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {jwt}",
            },
            json={"data": metadata},
        )
    resp.raise_for_status()
    data = resp.json()
    return cast(dict[str, Any], data.get("user_metadata") or {})
