from __future__ import annotations

import json
import time

import httpx

from monitoring_cli.config import Profile

_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
_MAX_POLL_INTERVAL = 30


def _device_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/auth/device"


def _token_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/token"


def start_device_flow(profile: Profile) -> dict:
    resp = httpx.post(
        _device_url(profile),
        data={"client_id": profile.client_id, "scope": "openid profile email roles"},
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


def get_access_token(profile: Profile) -> str:
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
        return resp.json()["access_token"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise AuthError("Token endpoint returned no access_token") from exc


class DeviceFlowExpiredError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


class AuthError(Exception):
    pass
