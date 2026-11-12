"""A queue on this machine for the account's limit of concurrent queries.

The server refuses a query (HTTP 429) when the account already runs its limit.
A command first takes one of that many lock files, so commands on one machine
wait in line here instead of all polling the server. Other machines and the
web app share the same limit, so the client still waits on a 429.
"""

from __future__ import annotations

import contextlib
import os
import random
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import IO

# Windows has no flock: there is no local queue, and the client still waits
# on the server's HTTP 429.
_HAS_FLOCK = sys.platform != "win32"
if _HAS_FLOCK:
    import fcntl

DEFAULT_SLOTS = 3
SLOTS_ENV = "DEDAUB_MONITORING_SLOTS"
STATE_DIR = Path.home() / ".config" / "dedaub" / "query-slots"


def slot_count() -> int:
    try:
        value = int(os.environ.get(SLOTS_ENV, ""))
    except ValueError:
        return DEFAULT_SLOTS
    return value if value > 0 else DEFAULT_SLOTS


class SlotWaitTimeout(Exception):
    pass


def _try_lock(path: Path) -> IO[bytes] | None:
    handle = open(path, "a+b")  # noqa: SIM115 - held until the slot is released
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


@contextlib.contextmanager
def hold(
    deadline: float,
    directory: Path = STATE_DIR,
    on_wait: Callable[[], None] | None = None,
    poll: float = 0.5,
) -> Iterator[None]:
    """Hold one slot until the block ends. Raise SlotWaitTimeout when no slot
    is free by `deadline` (time.monotonic()). When the lock files cannot be
    used at all, hold nothing and rely on the server."""
    if not _HAS_FLOCK:
        yield
        return
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        yield
        return
    count = slot_count()
    start = random.randrange(count)
    handle: IO[bytes] | None = None
    told = False
    while handle is None:
        for i in range(count):
            try:
                handle = _try_lock(directory / f"slot-{(start + i) % count}.lock")
            except OSError:
                yield  # unwritable directory: no local queue
                return
            if handle is not None:
                break
        if handle is not None:
            break
        if time.monotonic() >= deadline:
            raise SlotWaitTimeout()
        if not told and on_wait is not None:
            on_wait()
            told = True
        time.sleep(poll)
    try:
        yield
    finally:
        handle.close()
