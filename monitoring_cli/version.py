from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION = "monitoring-cli"


def cli_version() -> str:
    """The installed version of the CLI, or "unknown" when it is not installed."""
    try:
        return version(DISTRIBUTION)
    except PackageNotFoundError:
        return "unknown"
