"""The credentials file shared by the Dedaub CLIs.

dedaub-monitoring and the other Dedaub CLIs read and write the same file, so
one login serves them all. ``$DEDAUB_CONFIG`` points them at another file (tests, CI,
sandboxes).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "dedaub" / "monitoring.json"
CONFIG_ENV = "DEDAUB_CONFIG"
# A refresh token in this variable replaces the stored one, so CI jobs and
# containers can run with no config file and no browser login.
REFRESH_TOKEN_ENV = "DEDAUB_MONITORING_REFRESH_TOKEN"

DEFAULT_PROFILE = "prod"
DEFAULT_BASE_URL = "https://api.dedaub.com"
DEFAULT_OIDC_HOST = "https://auth.dedaub.com"
DEFAULT_CLIENT_ID = "watchdog-client"
DEFAULT_REALM = "dedaub"


def config_path() -> Path:
    """The config file in effect: ``$DEDAUB_CONFIG`` if set, else CONFIG_PATH."""
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()
    return CONFIG_PATH


@dataclass
class Profile:
    base_url: str
    oidc_host: str
    client_id: str
    realm: str = DEFAULT_REALM
    refresh_token: str | None = None


@dataclass
class Config:
    default: str
    profiles: dict[str, Profile] = field(default_factory=dict)

    @classmethod
    def load(cls) -> Config:
        path = config_path()
        if not path.exists():
            raise NotLoggedInError()
        try:
            data = json.loads(path.read_text())
            profiles = {k: Profile(**v) for k, v in data["profiles"].items()}
            return cls(default=data["default"], profiles=profiles)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ConfigError(
                f"Config file at {path} is corrupt or outdated: {e}"
            ) from e

    def save(self) -> None:
        path = config_path()
        parent = path.parent
        # mode= is subject to umask and skipped when the dir already exists,
        # so enforce owner-only perms explicitly to protect the refresh token.
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent.chmod(0o700)
        data = {
            "default": self.default,
            "profiles": {k: asdict(v) for k, v in self.profiles.items()},
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
        try:
            os.fchmod(tmp_fd, 0o600)
            with os.fdopen(tmp_fd, "w") as f:
                f.write(json.dumps(data, indent=2))
            os.replace(tmp_path, path)
        except Exception:
            os.unlink(tmp_path)
            raise

    def get_profile(self, name: str | None = None) -> Profile:
        key = name or self.default
        if key not in self.profiles:
            raise ProfileNotFoundError(key)
        return self.profiles[key]

    def upsert_profile(self, name: str, profile: Profile) -> None:
        self.profiles[name] = profile

    def remove_profile(self, name: str) -> None:
        if name not in self.profiles:
            raise ProfileNotFoundError(name)
        del self.profiles[name]


def persist_refresh_token(profile_name: str, old: str | None, new: str) -> bool:
    """Write a rotated refresh token back to the config file, atomically.

    Re-reads the file first so a concurrent change to other profiles (or by the
    other CLI) is not clobbered. Only replaces the token when the stored one is
    still the token we refreshed with, so a newer login is never overwritten by
    a stale rotation. Returns True when the file was updated; raises
    ConfigError or OSError when the file can't be read or written.
    """
    try:
        config = Config.load()
    except NotLoggedInError:
        return False
    profile = config.profiles.get(profile_name)
    if profile is None or profile.refresh_token not in (old, None):
        return False
    profile.refresh_token = new
    config.save()
    return True


class NotLoggedInError(Exception):
    pass


class ProfileNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Profile '{name}' not found")


class ConfigError(Exception):
    pass
