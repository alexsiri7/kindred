"""Shared environment settings for both backends.

Both ``mcp/settings.py`` and ``web/backend/settings.py`` subclass
``CoreSettings`` to add backend-specific fields. Both subclasses (and the
``settings`` instance below) read the same ``.env`` independently, so a
single env-var name reaches all three.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    supabase_url: str = ""
    supabase_anon_key: str = ""
    # HS256 path. RS256/JWKS support is the planned upgrade once we know the
    # production project's signing algorithm.
    supabase_jwt_secret: str = ""

    requesty_api_key: str = ""
    requesty_base_url: str = "https://router.requesty.ai/v1"

    sentry_dsn: str = ""


settings = CoreSettings()
