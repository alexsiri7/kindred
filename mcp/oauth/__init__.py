"""OAuth 2.1 + RFC 9728/8414/7591/8707 Authorization Server endpoints.

These routes are registered on the FastMCP server via ``mcp.custom_route()``,
which (per the FastMCP docstring) bypasses authorization. That is required:
discovery and OAuth endpoints must be reachable unauthenticated, otherwise
Claude.ai cannot discover the auth server in the first place.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from oauth.routes import (
    oauth_authorization_server,
    oauth_authorize,
    oauth_callback,
    oauth_protected_resource,
    oauth_register,
    oauth_token,
)


def register_routes(mcp: FastMCP) -> None:
    """Attach the six OAuth + discovery endpoints to ``mcp``."""
    mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])(
        oauth_protected_resource
    )
    mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])(
        oauth_authorization_server
    )
    mcp.custom_route("/oauth/register", methods=["POST"])(oauth_register)
    mcp.custom_route("/oauth/authorize", methods=["GET"])(oauth_authorize)
    mcp.custom_route("/oauth/callback", methods=["GET"])(oauth_callback)
    mcp.custom_route("/oauth/token", methods=["POST"])(oauth_token)


__all__ = ["register_routes"]
