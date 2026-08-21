"""Shared RCON transport failure handling.

The games do not distinguish transport faults consistently.  Keeping that
normalisation here means HLL and HLL:V use the same retry policy and gives
callers a useful, non-secret diagnostic category.
"""

from __future__ import annotations

import random
import socket
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum

from rcon.connection import HLLBrokenConnectionError, HLLCommandError


class TransportErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    CONNECTION_REFUSED = "connection_refused"
    CONNECTION_RESET = "connection_reset"
    BROKEN_PIPE = "broken_pipe"
    TIMEOUT = "timeout"
    SERVER_INTERNAL = "server_internal"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TransportFailure:
    """A safe-to-log classification of a failed RCON operation."""

    kind: TransportErrorKind
    retryable: bool


def classify_transport_failure(error: BaseException) -> TransportFailure:
    """Classify errors without relying on platform-specific error text."""
    if isinstance(error, HLLCommandError):
        if error.status_code == 401:
            return TransportFailure(TransportErrorKind.AUTHENTICATION, False)
        if error.status_code >= 500:
            return TransportFailure(TransportErrorKind.SERVER_INTERNAL, True)
        return TransportFailure(TransportErrorKind.UNKNOWN, False)

    if isinstance(error, (socket.timeout, TimeoutError)):
        return TransportFailure(TransportErrorKind.TIMEOUT, True)
    if isinstance(error, UnicodeDecodeError):
        return TransportFailure(TransportErrorKind.OFFLINE, True)
    if isinstance(error, ConnectionRefusedError):
        return TransportFailure(TransportErrorKind.CONNECTION_REFUSED, True)
    if isinstance(error, ConnectionResetError):
        return TransportFailure(TransportErrorKind.CONNECTION_RESET, True)
    if isinstance(error, BrokenPipeError):
        return TransportFailure(TransportErrorKind.BROKEN_PIPE, True)
    if isinstance(error, HLLCommandFailedError):
        return TransportFailure(TransportErrorKind.SERVER_INTERNAL, True)
    if isinstance(error, HLLBrokenConnectionError):
        return TransportFailure(TransportErrorKind.OFFLINE, True)
    if isinstance(error, RuntimeError):
        # Existing callers use RuntimeError for an interrupted socket state.
        return TransportFailure(TransportErrorKind.OFFLINE, True)
    if isinstance(error, OSError):
        return TransportFailure(TransportErrorKind.OFFLINE, True)
    return TransportFailure(TransportErrorKind.UNKNOWN, False)


def retry_delay_seconds(
    attempt: int, *, base_delay: float = 0.25, max_delay: float = 8.0, jitter: float = 0.2
) -> float:
    """Return capped exponential backoff with bounded jitter.

    ``attempt`` starts at zero.  Jitter prevents multiple pollers from
    reconnecting to a recovering game server at exactly the same moment.
    """
    exponential = min(max_delay, base_delay * (2 ** max(0, attempt)))
    return max(0.0, exponential + random.uniform(-jitter, jitter) * exponential)


@dataclass
class CommandRetryGate:
    """Small per-command circuit breaker used by one server controller."""

    failures: int = 0
    retry_after: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def begin_retry(self) -> float:
        """Reserve a retry and return its delay, serialising matching commands."""
        with self.lock:
            now = time.monotonic()
            wait_for_open_circuit = max(0.0, self.retry_after - now)
            delay = retry_delay_seconds(self.failures)
            self.failures += 1
            self.retry_after = now + wait_for_open_circuit + delay
            return wait_for_open_circuit + delay

    def record_success(self) -> None:
        with self.lock:
            self.failures = 0
            self.retry_after = 0.0
