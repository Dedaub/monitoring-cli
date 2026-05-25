from __future__ import annotations

import time

import httpx

from monitoring_cli.config import Profile

_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


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


def poll_token(profile: Profile, device_code: str, interval: int) -> str:
    while True:
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
        except httpx.HTTPError as exc:
            raise AuthError(f"Network error during device flow polling: {exc}") from exc
        data = resp.json()
        if resp.is_success:
            return data["refresh_token"]
        error = data.get("error", "")
        if error == "expired_token":
            raise DeviceFlowExpiredError()
        if error == "slow_down":
            interval += 5
        elif error not in ("authorization_pending",):
            raise AuthError(data.get("error_description", error))


def get_access_token(profile: Profile) -> str:
    resp = httpx.post(
        _token_url(profile),
        data={
            "grant_type": "refresh_token",
            "refresh_token": profile.refresh_token,
            "client_id": profile.client_id,
        },
        timeout=30,
    )
    if resp.status_code in (400, 401):
        raise SessionExpiredError()
    resp.raise_for_status()
    return resp.json()["access_token"]


class DeviceFlowExpiredError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


class AuthError(Exception):
    pass
