"""OAuth 2.1 endpoints for the Kindred MCP server.

Implements the MCP Authorization spec
(https://modelcontextprotocol.io/specification/draft/basic/authorization):

  - GET  /.well-known/oauth-protected-resource     (RFC 9728)
  - GET  /.well-known/oauth-authorization-server   (RFC 8414)
  - POST /oauth/register                            (RFC 7591)
  - GET  /oauth/authorize  → 302 to web app /mcp-auth relay page
  - POST /oauth/code-from-session ← web app posts Supabase token after OAuth
  - POST /oauth/token      → issues HS256 JWT (and refresh token)

Routes are registered as ``@mcp.custom_route()`` on the FastMCP instance via
``register_routes(mcp_obj)`` — invoked from ``main.py`` after the FastMCP
instance is constructed (avoids circular imports).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from mcp.server.fastmcp import FastMCP
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from oauth_state import (
    _state_lock,
    auth_codes,
    cleanup_and_pop,
    cleanup_and_store,
    oauth_sessions,
    refresh_tokens,
    registered_clients,
)
from services.oauth_store import delete_refresh_token, save_refresh_token, save_registered_client
from settings import settings

logger = logging.getLogger(__name__)

AUTH_CODE_TTL_SECONDS = 60 * 10  # 10 minutes
SESSION_TTL_SECONDS = 60 * 10  # 10 minutes
JWT_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days
REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days

WEB_APP_ORIGIN = "https://kindred.interstellarai.net"

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": WEB_APP_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _base_url() -> str:
    """Public base URL of the MCP server (no trailing slash). Raises 501 if unset."""
    if not settings.mcp_base_url:
        raise HTTPException(status_code=501, detail="MCP_BASE_URL not configured")
    return settings.mcp_base_url.rstrip("/")


def _create_jwt(user_id: str, email: str | None) -> str:
    """Mint an HS256 JWT signed with ``settings.secret_key``."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + JWT_EXPIRY_SECONDS,
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _pkce_s256(verifier: str) -> str:
    """Compute ``BASE64URL(SHA256(verifier))`` with no padding (RFC 7636 §4.6)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _issue_token_response(
    user_id: str, email: str | None, client_id: str, scope: str
) -> JSONResponse:
    """RFC 6749 token response with a fresh access_token + rotated refresh_token."""
    if not settings.secret_key:
        raise HTTPException(status_code=501, detail="SECRET_KEY not configured")

    now = datetime.now(UTC)
    access_token = _create_jwt(user_id, email)
    refresh_token = secrets.token_urlsafe(32)
    entry = {
        "user_id": user_id,
        "email": email,
        "client_id": client_id,
        "scope": scope,
        "expires_at": now + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
        "access_token_issued_at": now,
    }
    cleanup_and_store(refresh_tokens, refresh_token, entry)
    save_refresh_token(refresh_token, entry)
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRY_SECONDS,
            "refresh_token": refresh_token,
            "scope": scope,
        }
    )


_PROACTIVE_REFRESH_BUFFER = timedelta(minutes=5)


def _proactive_refresh() -> None:
    """On startup: scan loaded sessions and handle near-expiry or dead tokens.

    For each loaded refresh-token session:
    - If the refresh token is expired: log a warning and remove from memory.
      On their next request the client will receive a 401, prompting
      re-authentication.
    - If the access token is expired or within ``_PROACTIVE_REFRESH_BUFFER``:
      reset ``access_token_issued_at`` so the next ``POST /oauth/token`` call
      from the client unconditionally mints a fresh JWT (no refresh-token
      rotation — the client must still hold the old refresh token to request
      new tokens via the normal grant).

    This function is called once at startup inside ``build_app()``. When the
    persistent session store (planned in issue #125) is in place, it will run
    after sessions have been hydrated into ``refresh_tokens``. Until then it
    operates only on in-memory sessions established in the current process.
    It is a no-op when the dict is empty (fresh deployment, no persisted sessions).
    """
    if not settings.secret_key:
        logger.warning("proactive_refresh: SECRET_KEY not set, skipping")
        return

    now = datetime.now(UTC)
    access_cutoff = now + _PROACTIVE_REFRESH_BUFFER

    with _state_lock:
        keys = list(refresh_tokens.keys())
    # NOTE: mutations below are intentionally lock-free.
    # _proactive_refresh() runs synchronously in build_app() before the ASGI
    # server starts accepting connections, so no concurrent request handlers
    # can race against us. If this is ever moved to a background task,
    # mutations must be re-protected with _state_lock.

    refreshed = 0
    dropped = 0
    for token_key in keys:
        try:
            entry = refresh_tokens.get(token_key)
            if entry is None:
                continue  # evicted between snapshot and iteration (defensive)

            # --- expired refresh token: drop it ---
            refresh_exp = entry.get("expires_at")
            if (
                refresh_exp is not None
                and isinstance(refresh_exp, datetime)
                and now > refresh_exp
            ):
                refresh_tokens.pop(token_key, None)
                logger.warning(
                    "proactive_refresh: refresh token for user %s expired at %s — "
                    "user must re-authenticate",
                    entry.get("user_id", "unknown"),
                    refresh_exp.isoformat(),
                )
                dropped += 1
                continue

            # --- near-expiry or expired access token: flag for refresh ---
            issued_at: datetime | None = entry.get("access_token_issued_at")
            if issued_at is None:
                continue  # old record without the field; skip until next normal refresh

            user_id = entry.get("user_id")
            if user_id is None:
                logger.warning(
                    "proactive_refresh: skipping entry %r — missing user_id",
                    token_key[:8],
                )
                continue

            access_exp = issued_at + timedelta(seconds=JWT_EXPIRY_SECONDS)
            if access_exp <= access_cutoff:
                # Reset the clock so the next POST /oauth/token sees this as needing
                # a fresh JWT. Actual JWT minting happens in _issue_token_response on
                # the client's next request — we cannot push a token without a round-trip.
                entry["access_token_issued_at"] = now - timedelta(seconds=JWT_EXPIRY_SECONDS)
                logger.info(
                    "proactive_refresh: flagged user %s for access token refresh "
                    "(old token expired at %s)",
                    user_id,
                    access_exp.isoformat(),
                )
                refreshed += 1

        except Exception:
            logger.warning(
                "proactive_refresh: unexpected error processing entry %r — skipping",
                token_key[:8],
                exc_info=True,
            )

    if refreshed or dropped:
        logger.info(
            "proactive_refresh complete: %d refreshed, %d dropped (expired refresh tokens)",
            refreshed,
            dropped,
        )


async def _verify_supabase_token(access_token: str) -> dict[str, Any] | None:
    """Verify a Supabase access token via /auth/v1/user.

    Returns the user payload dict on success, or ``None`` if the network call
    fails or Supabase rejects the token. Extracted from the route handler so
    tests can stub it without monkey-patching ``httpx`` globally.

    Uses the Supabase REST API rather than local JWT decode so verification
    works regardless of the project's signing algorithm (HS256 vs RS256).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        if resp.status_code != 200:
            logger.warning(
                "MCP OAuth: Supabase /auth/v1/user returned %s", resp.status_code
            )
            return None
        payload = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("MCP OAuth: Supabase user lookup failed: %s", exc)
        return None
    except ValueError as exc:
        logger.warning("MCP OAuth: Supabase /auth/v1/user returned non-JSON body: %s", exc)
        return None
    if not isinstance(payload, dict):
        logger.warning(
            "MCP OAuth: Supabase /auth/v1/user returned non-dict payload (type=%s)",
            type(payload).__name__,
        )
        return None
    return payload


def register_routes(mcp_obj: FastMCP) -> None:
    """Register all OAuth + discovery routes on the given FastMCP instance.

    Called from ``main.py`` after ``mcp = FastMCP(...)`` is constructed. Using
    a function (rather than module-level decorators) avoids the ``main → oauth
    → main`` circular import that would otherwise occur.
    """

    # -----------------------------------------------------------------------
    # RFC 9728: Protected Resource Metadata
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])  # type: ignore[untyped-decorator]
    async def protected_resource_metadata(_request: Request) -> Response:
        base = _base_url()
        return JSONResponse(
            {
                "resource": f"{base}/mcp",
                "authorization_servers": [base],
                "scopes_supported": ["mcp"],
                "bearer_methods_supported": ["header"],
            }
        )

    # -----------------------------------------------------------------------
    # RFC 8414: Authorization Server Metadata
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])  # type: ignore[untyped-decorator]
    async def authorization_server_metadata(_request: Request) -> Response:
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

    # -----------------------------------------------------------------------
    # RFC 7591: Dynamic Client Registration
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/oauth/register", methods=["POST"])  # type: ignore[untyped-decorator]
    async def oauth_register(request: Request) -> Response:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}

        client_id = uuid.uuid4().hex
        client_secret = secrets.token_urlsafe(32)
        client = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": body.get("redirect_uris", []),
            "client_name": body.get("client_name", ""),
            "grant_types": body.get("grant_types", ["authorization_code"]),
            "response_types": body.get("response_types", ["code"]),
            "token_endpoint_auth_method": body.get(
                "token_endpoint_auth_method", "client_secret_post"
            ),
            "scope": body.get("scope", "mcp"),
        }
        cleanup_and_store(registered_clients, client_id, client)
        save_registered_client(client_id, client)
        logger.info(
            "MCP OAuth: registered client %s (%s)",
            client_id,
            client["client_name"],
        )
        return JSONResponse(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": client["redirect_uris"],
                "client_name": client["client_name"],
                "grant_types": client["grant_types"],
                "response_types": client["response_types"],
                "token_endpoint_auth_method": client["token_endpoint_auth_method"],
                "scope": client["scope"],
            },
            status_code=201,
        )

    # -----------------------------------------------------------------------
    # Authorization endpoint — redirects to web-app OAuth relay
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/oauth/authorize", methods=["GET"])  # type: ignore[untyped-decorator]
    async def oauth_authorize(request: Request) -> Response:
        if not settings.secret_key:
            raise HTTPException(status_code=501, detail="SECRET_KEY not configured")

        qp = request.query_params
        client_id = qp.get("client_id", "")
        redirect_uri = qp.get("redirect_uri", "")
        client_state = qp.get("state", "")
        code_challenge = qp.get("code_challenge", "")
        code_challenge_method = qp.get("code_challenge_method", "S256")
        scope = qp.get("scope", "mcp")
        response_type = qp.get("response_type", "code")

        if response_type != "code":
            raise HTTPException(
                status_code=400, detail="Only response_type=code is supported"
            )
        if code_challenge_method != "S256":
            raise HTTPException(
                status_code=400,
                detail="Only code_challenge_method=S256 is supported",
            )
        if not redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri is required")
        if not code_challenge:
            raise HTTPException(
                status_code=400, detail="code_challenge is required (PKCE required)"
            )
        registered = registered_clients.get(client_id)
        if not registered:
            raise HTTPException(
                status_code=400,
                detail="Unknown client_id — register first via POST /oauth/register",
            )
        if redirect_uri not in registered.get("redirect_uris", []):
            raise HTTPException(
                status_code=400, detail="redirect_uri not registered for this client"
            )

        flow_key = secrets.token_urlsafe(32)
        cleanup_and_store(
            oauth_sessions,
            flow_key,
            {
                "client_state": client_state,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "client_id": client_id,
                "scope": scope,
                "expires_at": datetime.now(UTC)
                + timedelta(seconds=SESSION_TTL_SECONDS),
            },
        )
        logger.info(
            "MCP OAuth: authorize → web-app relay for client %s (flow %s… stored_keys=%r)",
            client_id,
            flow_key[:12],
            [k[:8] for k in oauth_sessions],
        )
        return RedirectResponse(
            url=f"{WEB_APP_ORIGIN}/mcp-auth?flow={flow_key}",
            status_code=302,
        )

    # -----------------------------------------------------------------------
    # Code-from-session — called by the web-app relay after Supabase OAuth
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/oauth/code-from-session", methods=["POST", "OPTIONS"])  # type: ignore[untyped-decorator]
    async def oauth_code_from_session(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response(headers=_CORS_HEADERS)

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "JSON body required"},
                status_code=400,
                headers=_CORS_HEADERS,
            )

        flow_id = str(body.get("flow_id", ""))
        access_token = str(body.get("access_token", ""))

        logger.info(
            "MCP OAuth: code-from-session received flow_id=%r len=%d known_keys=%r",
            flow_id[:12] if flow_id else "",
            len(flow_id),
            [k[:8] for k in oauth_sessions],
        )

        if not flow_id or not access_token:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "flow_id and access_token required",
                },
                status_code=400,
                headers=_CORS_HEADERS,
            )

        session = cleanup_and_pop(oauth_sessions, flow_id)
        if not session:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Invalid or expired flow_id"},
                status_code=400,
                headers=_CORS_HEADERS,
            )

        user_data = await _verify_supabase_token(access_token)
        if user_data is None:
            return JSONResponse(
                {"error": "server_error", "error_description": "Token verification failed"},
                status_code=400,
                headers=_CORS_HEADERS,
            )
        user_id = user_data.get("id")
        email = user_data.get("email")
        if not user_id:
            return JSONResponse(
                {"error": "server_error", "error_description": "No user ID in token"},
                status_code=400,
                headers=_CORS_HEADERS,
            )

        kindred_auth_code = secrets.token_urlsafe(32)
        cleanup_and_store(
            auth_codes,
            kindred_auth_code,
            {
                "user_id": str(user_id),
                "email": email,
                "code_challenge": session["code_challenge"],
                "code_challenge_method": session["code_challenge_method"],
                "redirect_uri": session["redirect_uri"],
                "scope": session.get("scope", "mcp"),
                "client_id": session["client_id"],
                "expires_at": datetime.now(UTC)
                + timedelta(seconds=AUTH_CODE_TTL_SECONDS),
            },
        )

        params = {"code": kindred_auth_code, "state": session["client_state"]}
        redirect_url = f"{session['redirect_uri']}?{urlencode(params)}"
        logger.info(
            "MCP OAuth: code-from-session complete for client %s → %s",
            session["client_id"],
            session["redirect_uri"],
        )
        return JSONResponse({"redirect_url": redirect_url}, headers=_CORS_HEADERS)

    # -----------------------------------------------------------------------
    # Token endpoint
    # -----------------------------------------------------------------------
    @mcp_obj.custom_route("/oauth/token", methods=["POST"])  # type: ignore[untyped-decorator]
    async def oauth_token(request: Request) -> Response:
        if not settings.secret_key:
            raise HTTPException(status_code=501, detail="SECRET_KEY not configured")

        form = await request.form()
        grant_type = str(form.get("grant_type", ""))

        if grant_type == "refresh_token":
            refresh_token = str(form.get("refresh_token", ""))
            if not refresh_token:
                raise HTTPException(
                    status_code=400, detail="refresh_token is required"
                )
            session = cleanup_and_pop(refresh_tokens, refresh_token)
            if not session:
                raise HTTPException(
                    status_code=400, detail="Invalid or expired refresh_token"
                )
            delete_refresh_token(refresh_token)
            return _issue_token_response(
                session["user_id"],
                session.get("email"),
                session["client_id"],
                session.get("scope", "mcp"),
            )

        if grant_type != "authorization_code":
            raise HTTPException(status_code=400, detail="Unsupported grant_type")

        code = str(form.get("code", ""))
        redirect_uri = str(form.get("redirect_uri", ""))
        client_id = str(form.get("client_id", ""))
        code_verifier = str(form.get("code_verifier", ""))

        session = cleanup_and_pop(auth_codes, code)
        if not session:
            raise HTTPException(
                status_code=400, detail="Invalid or expired authorization code"
            )
        if redirect_uri != session["redirect_uri"]:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")

        if session.get("code_challenge_method") == "S256":
            if not code_verifier:
                raise HTTPException(
                    status_code=400, detail="code_verifier is required"
                )
            if _pkce_s256(code_verifier) != session["code_challenge"]:
                raise HTTPException(status_code=400, detail="PKCE verification failed")

        return _issue_token_response(
            session["user_id"],
            session.get("email"),
            client_id or session.get("client_id", ""),
            session.get("scope", "mcp"),
        )
