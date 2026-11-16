"""The credentials file shared by the Dedaub CLIs.

dedaub-monitoring and the other Dedaub CLIs read and write the same file, so
one login serves them all. ``$DEDAUB_CONFIG`` points them at another file (tests, CI,
sandboxes).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from collections.abc import Iterator
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


def _ensure_dir(parent: Path) -> None:
    """Make the folder of the config file, owner-only when it is ours.

    mode= is subject to umask and skipped when the folder already exists, so
    set 0700 explicitly. Do it only for a folder made here or for the default
    folder: a ``$DEDAUB_CONFIG`` file can sit in a shared folder such as /tmp
    or the working directory, and its mode is not ours to change.
    """
    created = not parent.exists()
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if created or parent == CONFIG_PATH.parent:
        parent.chmod(0o700)


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """Hold an exclusive lock on the config file while you read and write it.

    Several CLIs share the file. Without the lock, two read-change-write
    cycles at the same time lose one of the changes. The lock is an advisory
    flock on a ``.lock`` file next to the config file. On Windows there is no
    flock, so this does not lock.
    """
    path = config_path()
    _ensure_dir(path.parent)
    fd = os.open(path.with_name(path.name + ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if sys.platform != "win32":
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing the fd releases the flock


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
        # ValueError covers bad JSON and bad UTF-8; AttributeError a
        # "profiles" that is not an object; OSError a path that is a folder
        # or cannot be read.
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
            raise ConfigError(
                f"Config file at {path} is corrupt or outdated: {e}"
            ) from e

    def save(self) -> None:
        path = config_path()
        parent = path.parent
        _ensure_dir(parent)
        data = {
            "default": self.default,
            "profiles": {k: asdict(v) for k, v in self.profiles.items()},
        }
        tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
        try:
            with os.fdopen(tmp_fd, "w") as f:
                os.fchmod(f.fileno(), 0o600)
                f.write(json.dumps(data, indent=2))
                f.flush()
                # A crash after the rename must not leave an empty file.
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
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

    Re-reads the file under locked(), so a change by another process (another
    profile, a login, a logout, the other CLI) is not lost. Only replaces the
    token when the stored one is still the token we refreshed with, so a newer
    login is never overwritten by a stale rotation. Returns True when the file
    was updated; raises ConfigError or OSError when the file can't be read or
    written.
    """
    with locked():
        try:
            config = Config.load()
        except NotLoggedInError:
            return False
        profile = config.profiles.get(profile_name)
        if profile is None or profile.refresh_token != old:
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
