import sys
import time

import pytest

from monitoring_cli import slots

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="no flock on Windows")


def test_second_holder_waits_and_times_out(tmp_path, monkeypatch):
    monkeypatch.setenv(slots.SLOTS_ENV, "1")
    told = []
    with (
        slots.hold(time.monotonic() + 1, tmp_path),
        pytest.raises(slots.SlotWaitTimeout),
        slots.hold(
            time.monotonic() + 0.2, tmp_path, on_wait=lambda: told.append(1), poll=0.05
        ),
    ):
        pass
    assert told == [1]


def test_a_released_slot_can_be_taken_again(tmp_path, monkeypatch):
    monkeypatch.setenv(slots.SLOTS_ENV, "1")
    with slots.hold(time.monotonic() + 1, tmp_path):
        pass
    with slots.hold(time.monotonic() + 0.2, tmp_path, poll=0.05):
        pass


def test_holders_up_to_the_count_do_not_wait(tmp_path, monkeypatch):
    monkeypatch.setenv(slots.SLOTS_ENV, "2")
    with (
        slots.hold(time.monotonic() + 0.2, tmp_path, poll=0.05),
        slots.hold(time.monotonic() + 0.2, tmp_path, poll=0.05),
    ):
        pass


@pytest.mark.parametrize("value", ["", "x", "0", "-1"])
def test_slot_count_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv(slots.SLOTS_ENV, value)
    assert slots.slot_count() == slots.DEFAULT_SLOTS
