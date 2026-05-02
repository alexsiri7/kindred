"""Server-side Supabase PKCE code exchange.

Uses the *anon* key (the PKCE code-for-session flow is a public-flow operation)
and a separate Supabase client from ``mcp/db.py`` (which uses the service-role
key). Wraps the sync supabase-py call in ``asyncio.to_thread`` per the same
precedent as ``mcp/db.py:33``.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from oauth.state import base_url
from settings import settings


@lru_cache(maxsize=1)
def _anon_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


async def exchange_code(code: str, code_verifier: str) -> str:
    """Exchange a Supabase auth code for a session and return ``user.id``.

    Raises ``ValueError`` with a stable string on any failure so callers can
    map to a 502 response.
    """
    client = _anon_client()
    redirect_to = f"{base_url()}/oauth/callback"

    def _do() -> Any:
        return client.auth.exchange_code_for_session(
            {
                "auth_code": code,
                "code_verifier": code_verifier,
                "redirect_to": redirect_to,
            }
        )

    try:
        result = await asyncio.to_thread(_do)
    except Exception as exc:  # supabase-py raises a variety of types
        raise ValueError(f"supabase exchange_code_for_session failed: {exc}") from exc

    user = getattr(result, "user", None) or getattr(getattr(result, "session", None), "user", None)
    user_id = getattr(user, "id", None) if user is not None else None
    if not user_id:
        raise ValueError("supabase exchange_code_for_session returned no user.id")
    return str(user_id)


__all__ = ["exchange_code"]
