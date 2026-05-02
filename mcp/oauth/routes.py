"""Six OAuth 2.1 + RFC 9728 / RFC 8414 / RFC 7591 / RFC 8707 handlers.

Registered on the FastMCP server via ``mcp.custom_route()`` from
``oauth/__init__.py:register_routes`` — those routes bypass the
``with_user_context`` middleware so they do not 401 on themselves.
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from oauth import state as oauth_state
from oauth import supabase as oauth_supabase
from settings import settings


def _base_url() -> str:
    return settings.mcp_base_url.rstrip("/") if settings.mcp_base_url else ""


def _error(code: str, description: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        {"error": code, "error_description": description}, status_code=status_code
    )


# ---------------------------------------------------------------------------
# Discovery endpoints
# ---------------------------------------------------------------------------


async def oauth_protected_resource(request: Request) -> Response:
    """RFC 9728 §3 — protected-resource metadata."""
    base = _base_url()
    return JSONResponse(
        {
            "resource": oauth_state.canonical_resource_url(),
            "authorization_servers": [base],
            "scopes_supported": ["mcp"],
            "bearer_methods_supported": ["header"],
        }
    )


async def oauth_authorization_server(request: Request) -> Response:
    """RFC 8414 §3 — authorization-server metadata."""
    base = _base_url()
    return JSONResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp"],
        }
    )


# ---------------------------------------------------------------------------
# Dynamic Client Registration (RFC 7591)
# ---------------------------------------------------------------------------


async def oauth_register(request: Request) -> Response:
    try:
        body = await request.json()
    except Exception:
        return _error("invalid_request", "request body must be valid JSON")
    if not isinstance(body, dict):
        return _error("invalid_request", "request body must be a JSON object")

    redirect_uris = body.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return _error("invalid_request", "redirect_uris must be a non-empty array")
    for uri in redirect_uris:
        if not isinstance(uri, str) or not uri:
            return _error("invalid_request", "every redirect_uri must be a non-empty string")

    client_name = body.get("client_name") or "MCP Client"
    if not isinstance(client_name, str):
        return _error("invalid_request", "client_name must be a string")

    record = oauth_state.register_client(redirect_uris=redirect_uris, client_name=client_name)
    return JSONResponse(
        {
            "client_id": record.client_id,
            "client_secret": record.client_secret,
            "client_id_issued_at": record.issued_at,
            "client_secret_expires_at": 0,
            "redirect_uris": list(record.redirect_uris),
            "client_name": record.client_name,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        status_code=201,
    )


# ---------------------------------------------------------------------------
# Authorization endpoint (delegates to Supabase Google OAuth)
# ---------------------------------------------------------------------------


async def oauth_authorize(request: Request) -> Response:
    qp = request.query_params
    client_id = qp.get("client_id", "")
    redirect_uri = qp.get("redirect_uri", "")
    response_type = qp.get("response_type", "")
    code_challenge = qp.get("code_challenge", "")
    code_challenge_method = qp.get("code_challenge_method", "")
    client_state = qp.get("state")
    resource = qp.get("resource")

    if response_type != "code":
        return _error("unsupported_response_type", "response_type must be 'code'")
    if code_challenge_method != "S256":
        return _error(
            "invalid_request", "code_challenge_method must be 'S256' (OAuth 2.1 requires PKCE S256)"
        )
    if not code_challenge:
        return _error("invalid_request", "code_challenge is required")

    client = oauth_state.get_client(client_id)
    if client is None:
        return _error("invalid_client", "unknown client_id")
    if redirect_uri not in client.redirect_uris:
        return _error("invalid_request", "redirect_uri is not registered for this client")

    canonical = oauth_state.canonical_resource_url()
    if resource is not None and resource != canonical:
        return _error(
            "invalid_target",
            f"resource indicator must be {canonical!r} (RFC 8707)",
        )
    bound_resource = resource or canonical

    supabase_verifier = secrets.token_urlsafe(64)
    supabase_challenge = oauth_state.derive_pkce_s256_challenge(supabase_verifier)

    session_token = oauth_state.start_session(
        client_id=client_id,
        client_redirect_uri=redirect_uri,
        client_state=client_state,
        client_code_challenge=code_challenge,
        client_code_challenge_method=code_challenge_method,
        resource=bound_resource,
        supabase_verifier=supabase_verifier,
    )

    supabase_url = (settings.supabase_url or "").rstrip("/")
    redirect_to = f"{_base_url()}/oauth/callback"
    upstream_qs = urlencode(
        {
            "provider": "google",
            "redirect_to": redirect_to,
            "flow_type": "pkce",
            "code_challenge": supabase_challenge,
            "code_challenge_method": "S256",
            "state": session_token,
        }
    )
    upstream_url = f"{supabase_url}/auth/v1/authorize?{upstream_qs}"
    return RedirectResponse(url=upstream_url, status_code=302)


# ---------------------------------------------------------------------------
# OAuth callback (Supabase → kindred)
# ---------------------------------------------------------------------------


async def oauth_callback(request: Request) -> Response:
    qp = request.query_params
    code = qp.get("code", "")
    incoming_state = qp.get("state", "")
    if not code or not incoming_state:
        return _error("invalid_request", "code and state are required")

    session = oauth_state.pop_session(incoming_state)
    if session is None:
        return _error("invalid_request", "unknown or expired state token")

    try:
        user_id = await oauth_supabase.exchange_code(code, session.supabase_verifier)
    except ValueError as exc:
        return _error("upstream_failure", str(exc), status_code=502)

    kindred_code = oauth_state.mint_auth_code(session, user_id)

    qs_parts: dict[str, str] = {"code": kindred_code}
    if session.client_state is not None:
        qs_parts["state"] = session.client_state
    redirect = f"{session.client_redirect_uri}?{urlencode(qs_parts)}"
    return RedirectResponse(url=redirect, status_code=302)


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------


async def oauth_token(request: Request) -> Response:
    try:
        form = await request.form()
    except Exception:
        return _error("invalid_request", "body must be application/x-www-form-urlencoded")
    grant_type = str(form.get("grant_type", ""))

    if grant_type == "authorization_code":
        return await _token_from_auth_code(form)
    if grant_type == "refresh_token":
        return await _token_from_refresh(form)
    return _error("unsupported_grant_type", f"grant_type {grant_type!r} is not supported")


async def _token_from_auth_code(form: Any) -> Response:
    code = str(form.get("code", ""))
    code_verifier = str(form.get("code_verifier", ""))
    client_id = str(form.get("client_id", ""))
    redirect_uri = str(form.get("redirect_uri", ""))
    raw_resource = form.get("resource")
    resource = str(raw_resource) if raw_resource is not None else None

    if not code or not code_verifier or not client_id or not redirect_uri:
        return _error(
            "invalid_request",
            "code, code_verifier, client_id, and redirect_uri are required",
        )

    try:
        record = oauth_state.redeem_auth_code(code, code_verifier, resource)
    except ValueError as exc:
        return _error("invalid_grant", str(exc))

    if record.client_id != client_id:
        return _error("invalid_grant", "client_id does not match the issued code")
    if record.redirect_uri != redirect_uri:
        return _error("invalid_grant", "redirect_uri does not match the issued code")

    audience = record.resource or oauth_state.canonical_resource_url()
    access_token = oauth_state.mint_access_jwt(user_id=record.user_id, audience=audience)
    refresh_token = oauth_state.mint_refresh_token(user_id=record.user_id, audience=audience)
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": "mcp",
        }
    )


async def _token_from_refresh(form: Any) -> Response:
    refresh_token = str(form.get("refresh_token", ""))
    if not refresh_token:
        return _error("invalid_request", "refresh_token is required")
    consumed = oauth_state.consume_refresh_token(refresh_token)
    if consumed is None:
        return _error("invalid_grant", "refresh_token is unknown or expired")
    user_id, audience = consumed
    new_access = oauth_state.mint_access_jwt(user_id=user_id, audience=audience)
    new_refresh = oauth_state.mint_refresh_token(user_id=user_id, audience=audience)
    return JSONResponse(
        {
            "access_token": new_access,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": new_refresh,
            "scope": "mcp",
        }
    )


__all__ = [
    "oauth_authorization_server",
    "oauth_authorize",
    "oauth_callback",
    "oauth_protected_resource",
    "oauth_register",
    "oauth_token",
]
