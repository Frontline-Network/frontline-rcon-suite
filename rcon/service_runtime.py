"""Small helpers for cooperatively managed long-running services."""

from __future__ import annotations

import time
from threading import Event


def stopping(stop_event: Event | None) -> bool:
    """Return whether a shared-runtime service was asked to stop."""

    return stop_event is not None and stop_event.is_set()


def wait(stop_event: Event | None, seconds: float) -> bool:
    """Sleep interruptibly and return ``True`` when stopping was requested."""

    if stop_event is None:
        time.sleep(max(0.0, seconds))
        return False
    return stop_event.wait(max(0.0, seconds))
