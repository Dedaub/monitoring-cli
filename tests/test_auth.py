import httpx
import pytest
import respx

from monitoring_cli.auth import (
    AuthError,
    DeviceFlowExpiredError,
    SessionExpiredError,
    get_access_token,
    poll_token,
    start_device_flow,
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
def test_get_access_token_returns_token():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "fresh-access-tok", "token_type": "Bearer"},
        )
    )
    token = get_access_token(PROFILE)
    assert token == "fresh-access-tok"


@respx.mock
def test_get_access_token_raises_session_expired():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={"error": "invalid_grant", "error_description": "Token is not active"},
        )
    )
    with pytest.raises(SessionExpiredError):
        get_access_token(PROFILE)


@respx.mock
def test_poll_token_raises_on_network_error(monkeypatch):
    monkeypatch.setattr("monitoring_cli.auth.time.sleep", lambda _: None)
    respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    with pytest.raises(AuthError):
        poll_token(PROFILE, "dev-code-123", interval=1)


@respx.mock
def test_get_access_token_raises_session_expired_on_401():
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            401,
            json={"error": "unauthorized"},
        )
    )
    with pytest.raises(SessionExpiredError):
        get_access_token(PROFILE)
