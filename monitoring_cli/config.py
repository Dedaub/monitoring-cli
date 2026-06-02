from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "dedaub" / "monitoring.json"


@dataclass
class Profile:
    base_url: str
    oidc_host: str
    client_id: str
    realm: str = "dedaub"
    refresh_token: str | None = None


@dataclass
class Config:
    default: str
    profiles: dict[str, Profile] = field(default_factory=dict)

    @classmethod
    def load(cls) -> Config:
        if not CONFIG_PATH.exists():
            raise NotLoggedInError()
        try:
            data = json.loads(CONFIG_PATH.read_text())
            profiles = {k: Profile(**v) for k, v in data["profiles"].items()}
            return cls(default=data["default"], profiles=profiles)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ConfigError(
                f"Config file at {CONFIG_PATH} is corrupt or outdated: {e}"
            ) from e

    def save(self) -> None:
        parent = CONFIG_PATH.parent
        # mode= is subject to umask and skipped when the dir already exists,
        # so enforce owner-only perms explicitly to protect the refresh token.
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent.chmod(0o700)
        data = {
            "default": self.default,
            "profiles": {k: asdict(v) for k, v in self.profiles.items()},
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent)
        try:
            os.fchmod(tmp_fd, 0o600)
            with os.fdopen(tmp_fd, "w") as f:
                f.write(json.dumps(data, indent=2))
            os.replace(tmp_path, CONFIG_PATH)
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


class NotLoggedInError(Exception):
    pass


class ProfileNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Profile '{name}' not found")


class ConfigError(Exception):
    pass
