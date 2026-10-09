import base64
import json

import httpx
import pytest
import respx

from monitoring_cli.auth import (
    AuthError,
    DeviceFlowExpiredError,
    SessionExpiredError,
    poll_token,
    refresh_tokens,
    revoke_token,
    start_device_flow,
    token_type,
)
from monitoring_cli.config import Profile

PROFILE = Profile(
    base_url="https://api.dedaub.com",
    oidc_host="https://auth.dedaub.com",
    client_id="watchdog-client",
    realm="dedaub",
    refresh_token="old-refresh-token",
)

DEVICE_URL = "https://auth.dedaub.com/realms/dedaub/protocol/openid-connect/auth/device"
TOKEN_URL = "https://auth.dedaub.com/realms/dedaub/protocol/openid-connect/token"
REVOKE_URL = "https://auth.dedaub.com/realms/dedaub/protocol/openid-connect/revoke"


@respx.mock
def test_start_device_flow_returns_device_info():
    respx.post(DEVICE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "device_code": "dev-code-123",
                "user_code": "ABCD-1234",
                "verification_uri": "https://auth.dedaub.com/activate",
                "verification_uri_complete": "https://auth.dedaub.com/activate?user_code=ABCD-1234",
                "expires_in": 600,
                "interval": 5,
            },
        )
    )
    result = start_device_flow(PROFILE)
    assert result["device_code"] == "dev-code-123"
    assert result["user_code"] == "ABCD-1234"
    assert result["interval"] == 5


@respx.mock
def test_poll_token_returns_refresh_token_on_success(monkeypatch):
    monkeypatch.setattr("monitoring_cli.auth.time.sleep", lambda _: None)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "acc-tok",
                "refresh_token": "new-refresh-tok",
                "token_type": "Bearer",
            },
        )
    )
    result = poll_token(PROFILE, "dev-code-123", interval=1)
    assert result == "new-refresh-tok"


@respx.mock
def test_poll_token_raises_on_expired(monkeypatch):
    monkeypatch.setattr("monitoring_cli.auth.time.sleep", lambda _: None)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={"error": "expired_token", "error_description": "Device code expired"},
        )
    )
    with pytest.raises(DeviceFlowExpiredError):
        poll_token(PROFILE, "dev-code-123", interval=1)


@respx.mock
def test_poll_token_keeps_polling_on_authorization_pending(monkeypatch):
    monkeypatch.setattr("monitoring_cli.auth.time.sleep", lambda _: None)
    responses = [
        httpx.Response(400, json={"error": "authorization_pending"}),
        httpx.Response(400, json={"error": "authorization_pending"}),
        httpx.Response(200, json={"access_token": "a", "refresh_token": "final-tok"}),
    ]
    respx.post(TOKEN_URL).side_effect = responses
    result = poll_token(PROFILE, "dev-code-123", interval=1)
    assert result == "final-tok"


@respx.mock
def test_refresh_tokens_returns_token():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "fresh-access-tok", "token_type": "Bearer"},
        )
    )
    tokens = refresh_tokens(PROFILE)
    assert tokens.access_token == "fresh-access-tok"
    assert tokens.refresh_token is None


@respx.mock
def test_refresh_tokens_raises_session_expired():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "Token is not active"},
        )
    )
    with pytest.raises(SessionExpiredError):
        refresh_tokens(PROFILE)


@respx.mock
def test_poll_token_raises_on_network_error(monkeypatch):
    monkeypatch.setattr("monitoring_cli.auth.time.sleep", lambda _: None)
    respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    with pytest.raises(AuthError):
        poll_token(PROFILE, "dev-code-123", interval=1)


@respx.mock
def test_refresh_tokens_raises_session_expired_on_401():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            401,
            json={"error": "unauthorized"},
        )
    )
    with pytest.raises(SessionExpiredError):
        refresh_tokens(PROFILE)


@respx.mock
def test_start_device_flow_requests_offline_access():
    route = respx.post(DEVICE_URL).mock(
        return_value=httpx.Response(200, json={"device_code": "d"})
    )
    start_device_flow(PROFILE)
    body = route.calls.last.request.content.decode()
    assert "offline_access" in body


@respx.mock
def test_refresh_tokens_returns_rotated_refresh_token():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "acc",
                "refresh_token": "rotated-refresh-tok",
                "expires_in": 300,
            },
        )
    )
    tokens = refresh_tokens(PROFILE)
    assert tokens.refresh_token == "rotated-refresh-tok"
    assert tokens.expires_in == 300


@respx.mock
def test_revoke_token_posts_refresh_token():
    route = respx.post(REVOKE_URL).mock(return_value=httpx.Response(200))
    revoke_token(PROFILE)
    body = route.calls.last.request.content.decode()
    assert "token_type_hint=refresh_token" in body
    assert "client_id=watchdog-client" in body
    assert "token=old-refresh-token" in body


@respx.mock
def test_revoke_token_raises_on_server_error():
    respx.post(REVOKE_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(AuthError):
        revoke_token(PROFILE)


@respx.mock
def test_revoke_token_raises_on_network_error():
    respx.post(REVOKE_URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(AuthError):
        revoke_token(PROFILE)


def _jwt(claims: dict) -> str:
    def seg(obj: dict) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{seg({'alg': 'none'})}.{seg(claims)}.sig"


def test_token_type_offline():
    assert token_type(_jwt({"typ": "Offline"})) == "Offline"


def test_token_type_refresh():
    assert token_type(_jwt({"typ": "Refresh"})) == "Refresh"


def test_token_type_missing_claim():
    assert token_type(_jwt({"sub": "u"})) is None


@pytest.mark.parametrize("token", ["opaque", "a.!!!.c", "a.bm90LWpzb24.c"])
def test_token_type_not_a_jwt(token):
    assert token_type(token) is None
