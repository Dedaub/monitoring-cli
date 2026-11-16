"""Keycloak OAuth2 device-flow login and access-token refresh."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from typing import NamedTuple

import httpx

from dedaub_auth.config import Profile

_DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
_MAX_POLL_INTERVAL = 30
# offline_access makes Keycloak issue an offline token: it outlives the browser
# SSO session and its idle window restarts on every refresh.
_SCOPE = "openid profile email roles offline_access"
# Refresh the access token this many seconds before it expires, so a request
# never leaves with a token that dies in flight.
EXPIRY_SKEW = 30.0
# Used when neither expires_in nor a JWT exp claim is available.
_FALLBACK_TTL = 60.0


class Tokens(NamedTuple):
    access_token: str
    # Keycloak rotates the refresh token on each refresh; the old one keeps its
    # original expiry, so callers must store this one to stay logged in.
    refresh_token: str | None
    # None when the token endpoint sent no expires_in.
    expires_in: float | None


def _device_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/auth/device"


def _token_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/token"


def _revoke_url(profile: Profile) -> str:
    return f"{profile.oidc_host}/realms/{profile.realm}/protocol/openid-connect/revoke"


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
    """Exchange the profile's refresh token for a fresh access token."""
    if not profile.refresh_token:
        raise SessionExpiredError()
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
    except json.JSONDecodeError as exc:
        raise AuthError("Token endpoint returned no access_token") from exc
    if not isinstance(data, dict) or not data.get("access_token"):
        raise AuthError("Token endpoint returned no access_token")
    expires_in = data.get("expires_in")
    return Tokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token") or None,
        expires_in=float(expires_in) if isinstance(expires_in, int | float) else None,
    )


def revoke_token(profile: Profile) -> None:
    try:
        resp = httpx.post(
            _revoke_url(profile),
            data={
                "token": profile.refresh_token,
                "token_type_hint": "refresh_token",
                "client_id": profile.client_id,
            },
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise AuthError(f"Network error revoking token: {exc}") from exc
    if resp.is_error:
        raise AuthError(f"Revocation endpoint returned HTTP {resp.status_code}")


def _jwt_claims(token: str) -> dict | None:
    # Unverified: only used for hints (which warning to show, when to refresh).
    # The server still verifies the token on each use.
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError):
        return None
    return claims if isinstance(claims, dict) else None


def token_type(token: str) -> str | None:
    """The ``typ`` claim of a JWT (``Offline`` for an offline token)."""
    typ = (_jwt_claims(token) or {}).get("typ")
    return typ if isinstance(typ, str) else None


def _jwt_exp(token: str) -> float | None:
    exp = (_jwt_claims(token) or {}).get("exp")
    return float(exp) if isinstance(exp, int | float) else None


class TokenManager:
    """Caches the access token and reports refresh-token rotation.

    The access token is reused until ``EXPIRY_SKEW`` seconds before it expires.
    ``on_rotate(old, new)`` is called whenever Keycloak returns a refresh token
    different from the one we sent; the profile is updated in place so later
    refreshes in this process use the new token.
    """

    def __init__(
        self,
        profile: Profile,
        on_rotate: Callable[[str | None, str], object] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._profile = profile
        self._on_rotate = on_rotate
        self._clock = clock
        self._token: str | None = None
        self._expires_at = 0.0

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0

    def get(self) -> str:
        now = self._clock()
        if self._token is not None and now < self._expires_at - EXPIRY_SKEW:
            return self._token
        tokens = refresh_tokens(self._profile)
        if tokens.expires_in is not None:
            self._expires_at = now + tokens.expires_in
        else:
            self._expires_at = _jwt_exp(tokens.access_token) or now + _FALLBACK_TTL
        self._token = tokens.access_token
        old = self._profile.refresh_token
        if tokens.refresh_token and tokens.refresh_token != old:
            self._profile.refresh_token = tokens.refresh_token
            if self._on_rotate is not None:
                self._on_rotate(old, tokens.refresh_token)
        return self._token


class DeviceFlowExpiredError(Exception):
    pass


class SessionExpiredError(Exception):
    pass


class AuthError(Exception):
    pass
