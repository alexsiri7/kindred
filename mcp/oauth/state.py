"""In-memory OAuth state + PKCE/JWT helpers.

All state is in-process; Railway runs a single MCP instance per service. Codes
are short-lived (10 min) and sessions are short-lived (5 min), so process
restarts only invalidate in-flight OAuth flows — Claude.ai retries the dance.
Persisting to Supabase is tracked as a follow-up.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import jwt

from settings import settings

_log = logging.getLogger(__name__)

_AUTH_CODE_TTL_S = 600  # 10 minutes
_ACCESS_TOKEN_TTL_S = 3600  # 1 hour
_REFRESH_TOKEN_TTL_S = 30 * 24 * 3600  # 30 days


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegisteredClient:
    client_id: str
    redirect_uris: tuple[str, ...]
    client_name: str
    issued_at: int


@dataclass
class AuthSession:
    """State held between /oauth/authorize and /oauth/callback."""

    client_id: str
    client_redirect_uri: str
    client_state: str | None
    client_code_challenge: str
    client_code_challenge_method: str
    resource: str
    supabase_verifier: str


@dataclass(frozen=True)
class AuthCode:
    code: str
    user_id: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    resource: str
    expires_at: int


@dataclass(frozen=True)
class RefreshTokenRecord:
    token: str
    user_id: str
    audience: str
    expires_at: int


# ---------------------------------------------------------------------------
# In-process stores. Single Uvicorn worker, so the pop()-based critical
# sections (redeem_auth_code, consume_refresh_token, pop_session) are atomic
# between awaits under asyncio cooperative scheduling — no asyncio.Lock
# needed at this scale. Scaling to >1 worker will require persistence.
# ---------------------------------------------------------------------------
_clients: dict[str, RegisteredClient] = {}
_sessions: dict[str, AuthSession] = {}
_codes: dict[str, AuthCode] = {}
_refresh: dict[str, RefreshTokenRecord] = {}


# ---------------------------------------------------------------------------
# Canonical resource URL
# ---------------------------------------------------------------------------


def canonical_resource_url() -> str:
    """Return ``<MCP_BASE_URL>/mcp`` with no trailing slash.

    Building it once and reusing avoids the trailing-slash mismatch pitfall
    documented in the research (claude-code issue #46539): a token minted with
    ``aud="https://x/mcp"`` will be rejected if validation expects
    ``"https://x/mcp/"``.

    Fails loud if ``MCP_BASE_URL`` is unset — RFC 8707 audience binding is
    defeated by a relative-URL ``aud`` claim, and silent fallbacks would mask
    misconfiguration until cross-host validation breaks.
    """
    base = settings.mcp_base_url.rstrip("/") if settings.mcp_base_url else ""
    if not base:
        raise RuntimeError(
            "MCP_BASE_URL is not configured; cannot derive canonical resource URL"
        )
    return urljoin(base + "/", "mcp")


# ---------------------------------------------------------------------------
# Client registration (RFC 7591)
# ---------------------------------------------------------------------------


def register_client(redirect_uris: list[str], client_name: str) -> RegisteredClient:
    client_id = secrets.token_urlsafe(24)
    record = RegisteredClient(
        client_id=client_id,
        redirect_uris=tuple(redirect_uris),
        client_name=client_name,
        issued_at=int(time.time()),
    )
    _clients[client_id] = record
    return record


def get_client(client_id: str) -> RegisteredClient | None:
    return _clients.get(client_id)


# ---------------------------------------------------------------------------
# Authorization session (kept between /authorize and /callback)
# ---------------------------------------------------------------------------


def start_session(
    *,
    client_id: str,
    client_redirect_uri: str,
    client_state: str | None,
    client_code_challenge: str,
    client_code_challenge_method: str,
    resource: str,
    supabase_verifier: str,
) -> str:
    session_token = secrets.token_urlsafe(32)
    _sessions[session_token] = AuthSession(
        client_id=client_id,
        client_redirect_uri=client_redirect_uri,
        client_state=client_state,
        client_code_challenge=client_code_challenge,
        client_code_challenge_method=client_code_challenge_method,
        resource=resource,
        supabase_verifier=supabase_verifier,
    )
    return session_token


def pop_session(session_token: str) -> AuthSession | None:
    return _sessions.pop(session_token, None)


# ---------------------------------------------------------------------------
# Authorization code (one-time, 10 min TTL)
# ---------------------------------------------------------------------------


def mint_auth_code(session: AuthSession, user_id: str) -> str:
    code = secrets.token_urlsafe(32)
    _codes[code] = AuthCode(
        code=code,
        user_id=user_id,
        client_id=session.client_id,
        redirect_uri=session.client_redirect_uri,
        code_challenge=session.client_code_challenge,
        code_challenge_method=session.client_code_challenge_method,
        resource=session.resource,
        expires_at=int(time.time()) + _AUTH_CODE_TTL_S,
    )
    return code


def redeem_auth_code(code: str, code_verifier: str, resource: str | None) -> AuthCode:
    """Pop the code first so concurrent reuse can't both succeed.

    Raises ``ValueError`` on any validation failure; caller should map to a
    400 ``invalid_grant`` response.
    """
    record = _codes.pop(code, None)
    if record is None:
        raise ValueError("unknown or already-redeemed code")
    if record.expires_at < int(time.time()):
        raise ValueError("authorization code expired")
    if record.code_challenge_method != "S256":
        raise ValueError("unsupported code_challenge_method")
    if not verify_pkce_s256(code_verifier, record.code_challenge):
        raise ValueError("PKCE verifier does not match challenge")
    if resource is not None and resource != record.resource:
        raise ValueError("resource indicator mismatch")
    return record


# ---------------------------------------------------------------------------
# PKCE S256 (RFC 7636 §4.6)
# ---------------------------------------------------------------------------


def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    derived = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(derived, code_challenge)


def derive_pkce_s256_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Access token (HS256 JWT)
# ---------------------------------------------------------------------------


def mint_access_jwt(
    *, user_id: str, audience: str, expires_in_s: int = _ACCESS_TOKEN_TTL_S
) -> str:
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured; cannot mint JWT")
    now = int(time.time())
    issuer = settings.mcp_base_url.rstrip("/") if settings.mcp_base_url else ""
    claims: dict[str, object] = {
        "iss": issuer,
        "sub": user_id,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in_s,
        "scope": "mcp",
    }
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


def verify_access_jwt(token: str, expected_audience: str) -> str | None:
    """Return the ``sub`` (user_id) on success, ``None`` on any failure.

    Failures are intentionally swallowed: the middleware will fall through to
    the connector-token DB lookup on ``None`` and only emit a 401 after both
    paths fail.
    """
    if not settings.secret_key:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=expected_audience,
            leeway=0,
        )
    except jwt.PyJWTError as exc:
        _log.info("JWT verification failed: %s", type(exc).__name__)
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


# ---------------------------------------------------------------------------
# Refresh token (opaque)
# ---------------------------------------------------------------------------


def mint_refresh_token(*, user_id: str, audience: str) -> str:
    token = secrets.token_urlsafe(48)
    _refresh[token] = RefreshTokenRecord(
        token=token,
        user_id=user_id,
        audience=audience,
        expires_at=int(time.time()) + _REFRESH_TOKEN_TTL_S,
    )
    return token


def consume_refresh_token(token: str) -> tuple[str, str] | None:
    """Pop the record (rotation: caller must mint a new refresh token)."""
    record = _refresh.pop(token, None)
    if record is None:
        return None
    if record.expires_at < int(time.time()):
        return None
    return record.user_id, record.audience


# ---------------------------------------------------------------------------
# Test helpers (used by mcp/tests/test_oauth.py)
# ---------------------------------------------------------------------------


def _reset_all_for_tests() -> None:
    _clients.clear()
    _sessions.clear()
    _codes.clear()
    _refresh.clear()


__all__ = [
    "AuthCode",
    "AuthSession",
    "RefreshTokenRecord",
    "RegisteredClient",
    "canonical_resource_url",
    "consume_refresh_token",
    "derive_pkce_s256_challenge",
    "get_client",
    "mint_access_jwt",
    "mint_auth_code",
    "mint_refresh_token",
    "pop_session",
    "redeem_auth_code",
    "register_client",
    "start_session",
    "verify_access_jwt",
    "verify_pkce_s256",
]
