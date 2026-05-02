from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    requesty_api_key: str = ""
    requesty_base_url: str = "https://router.requesty.ai/v1"

    sentry_dsn: str = ""

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    mcp_allowed_hosts: str = ""

    # MCP OAuth 2.1 (issue #11)
    mcp_base_url: str = "https://kindred-mcp.interstellarai.net"
    secret_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_anon_key: str = ""


settings = Settings()
