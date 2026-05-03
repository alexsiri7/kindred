from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    supabase_url: str = ""

    requesty_api_key: str = ""
    requesty_base_url: str = "https://router.requesty.ai/v1"

    sentry_dsn: str = ""

    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    mcp_base_url: str = ""
    secret_key: str = ""

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_allowed_hosts: str = ""

    # Per-user rate limiting (#42). Window is fixed at 60 seconds; see rate_limit.py.
    # 0 disables the global cap; per-tool caps still apply if configured.
    mcp_rate_limit_global_per_min: int = 60
    # Comma-separated `tool_name:limit_per_min` pairs (parsed in rate_limit.py).
    mcp_rate_limit_per_tool: str = "search_entries:10"
    # Kill-switch for incident response and unit tests that exercise tool wiring.
    mcp_rate_limit_disabled: bool = False


settings = Settings()
