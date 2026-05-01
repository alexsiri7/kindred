"""Supabase client factories.

Routes use ``user_client`` so RLS scopes every query to the caller. Only the
``connect.py`` token-mint route and ``DELETE /account`` use ``service_client``,
both of which intentionally need to bypass RLS.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from settings import settings


def user_client(user_jwt: str) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(user_jwt)
    return client


@lru_cache(maxsize=1)
def service_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
