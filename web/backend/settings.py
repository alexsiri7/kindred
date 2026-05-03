from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    supabase_url: str = ""
    supabase_anon_key: str = ""
    # HS256 path. RS256/JWKS support is the planned upgrade once we know the
    # production project's signing algorithm.
    supabase_jwt_secret: str = ""

    requesty_api_key: str = ""
    requesty_base_url: str = "https://router.requesty.ai/v1"

    sentry_dsn: str = ""

    web_host: str = "0.0.0.0"
    web_port: int = 8001


settings = Settings()
