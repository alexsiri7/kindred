from lib.settings import CoreSettings


class Settings(CoreSettings):
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
