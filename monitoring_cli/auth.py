from __future__ import annotations

import json
import time
from typing import NamedTuple

import httpx

from monitoring_cli.config import Profile

_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
_MAX_POLL_INTERVAL = 30
# offline_access makes Keycloak issue an offline token: it outlives the browser
# SSO session and its idle window restarts on every refresh.
_SCOPE = "openid profile email roles offline_access"


class Tokens(NamedTuple):
    access_token: str
    # Keycloak rotates the refresh token on each refresh; the old one keeps its
    # original expiry, so callers must store this one to stay logged in.
    refresh_token: str | None
    expires_in: int


def _device_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/auth/device"


def _token_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/token"


def start_device_flow(profile: Profile) -> dict:
    resp = httpx.post(
        _device_url(profile),
        data={"client_id": profile.client_id, "scope": _SCOPE},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def poll_token(
    profile: Profile, device_code: str, interval: int, expires_in: int = 600
) -> str:
    deadline = time.monotonic() + expires_in
    while time.monotonic() < deadline:
        time.sleep(interval)
        try:
            resp = httpx.post(
                _token_url(profile),
                data={
                    "grant_type": _DEVICE_GRANT,
                    "device_code": device_code,
                    "client_id": profile.client_id,
                },
                timeout=30,
            )
            data = resp.json()
        except httpx.HTTPError as exc:
            raise AuthError(f"Network error during device flow polling: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AuthError(
                f"Invalid response from token endpoint (status {resp.status_code})"
            ) from exc
        if resp.is_success:
            return data["refresh_token"]
        error = data.get("error", "")
        if error == "expired_token":
            raise DeviceFlowExpiredError()
        if error == "slow_down":
            interval = min(interval + 5, _MAX_POLL_INTERVAL)
        elif error != "authorization_pending":
            raise AuthError(data.get("error_description", error))
    raise DeviceFlowExpiredError()


def refresh_tokens(profile: Profile) -> Tokens:
    try:
        resp = httpx.post(
            _token_url(profile),
            data={
                "grant_type": "refresh_token",
                "refresh_token": profile.refresh_token,
                "client_id": profile.client_id,
            },
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise AuthError(f"Network error refreshing access token: {exc}") from exc
    if resp.status_code in (400, 401):
        raise SessionExpiredError()
    if resp.is_error:
        raise AuthError(f"Token endpoint returned HTTP {resp.status_code}")
    try:
        data = resp.json()
        return Tokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 60)),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AuthError("Token endpoint returned no access_token") from exc


class DeviceFlowExpiredError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


class AuthError(Exception):
    pass
