"""Direct unit tests for ``oauth._verify_supabase_token``.

The other suites stub the helper to keep the route tests hermetic; these tests
exercise the helper itself by intercepting the ``httpx`` call so each branch
(transport error, non-200, non-dict payload, non-JSON body, success) has direct
coverage. Without this, the ``isinstance`` narrowing and the new ``ValueError``
catch would have no test guarding against future regression.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

import oauth as oauth_module


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch via ``oauth_module.settings`` (not ``settings_module.settings``)
    # because ``test_settings.py`` calls ``importlib.reload(settings)`` and
    # diverges the two module-level references — ``oauth.py`` keeps its
    # original instance, so that's the one the helper actually reads.
    monkeypatch.setattr(
        oauth_module.settings, "supabase_url", "https://supabase.test.example.com"
    )
    monkeypatch.setattr(oauth_module.settings, "supabase_anon_key", "test-anon-key")


def _install_transport(
    monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport
) -> None:
    """Make ``httpx.AsyncClient(...)`` route through the given mock transport."""
    real_init = httpx.AsyncClient.__init__

    def _patched_init(self: httpx.AsyncClient, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = handler
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", _patched_init)


async def test_verify_returns_payload_on_200_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/user"
        assert request.headers["apikey"] == "test-anon-key"
        assert request.headers["Authorization"] == "Bearer abc"
        return httpx.Response(200, json={"id": "user-1", "email": "u@example.com"})

    _install_transport(monkeypatch, httpx.MockTransport(_handler))

    result = await oauth_module._verify_supabase_token("abc")
    assert result == {"id": "user-1", "email": "u@example.com"}


async def test_verify_returns_none_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    _install_transport(monkeypatch, httpx.MockTransport(_handler))

    assert await oauth_module._verify_supabase_token("abc") is None


async def test_verify_returns_none_on_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"msg": "invalid token"})

    _install_transport(monkeypatch, httpx.MockTransport(_handler))

    assert await oauth_module._verify_supabase_token("abc") is None


async def test_verify_returns_none_on_non_dict_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "a", "dict"])

    _install_transport(monkeypatch, httpx.MockTransport(_handler))

    assert await oauth_module._verify_supabase_token("abc") is None


async def test_verify_returns_none_on_non_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"<html>maintenance</html>", headers={"content-type": "text/html"}
        )

    _install_transport(monkeypatch, httpx.MockTransport(_handler))

    assert await oauth_module._verify_supabase_token("abc") is None
