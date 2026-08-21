import socket
from unittest.mock import patch

from rcon.connection import HLLBrokenConnectionError, HLLCommandError
from rcon.transport import (
    CommandRetryGate,
    TransportErrorKind,
    classify_transport_failure,
    retry_delay_seconds,
)


def test_classify_transport_failure_covers_expected_rcon_faults():
    cases = [
        (socket.timeout(), TransportErrorKind.TIMEOUT, True),
        (ConnectionRefusedError(), TransportErrorKind.CONNECTION_REFUSED, True),
        (ConnectionResetError(), TransportErrorKind.CONNECTION_RESET, True),
        (BrokenPipeError(), TransportErrorKind.BROKEN_PIPE, True),
        (HLLBrokenConnectionError("closed"), TransportErrorKind.OFFLINE, True),
        (HLLCommandError(401, "bad token"), TransportErrorKind.AUTHENTICATION, False),
        (HLLCommandError(504, "timeout"), TransportErrorKind.SERVER_INTERNAL, True),
        (HLLCommandError(400, "bad input"), TransportErrorKind.UNKNOWN, False),
    ]

    for error, kind, retryable in cases:
        failure = classify_transport_failure(error)
        assert failure.kind is kind
        assert failure.retryable is retryable


@patch("rcon.transport.random.uniform", return_value=0.0)
def test_backoff_is_exponential_and_capped(_random):
    assert retry_delay_seconds(0) == 0.25
    assert retry_delay_seconds(1) == 0.5
    assert retry_delay_seconds(20) == 8.0


@patch("rcon.transport.random.uniform", return_value=0.0)
@patch("rcon.transport.time.monotonic", side_effect=[10.0, 10.0])
def test_command_retry_gate_serializes_same_command(_clock, _random):
    gate = CommandRetryGate()

    assert gate.begin_retry() == 0.25
    assert gate.begin_retry() == 0.75

    gate.record_success()
    assert gate.failures == 0
    assert gate.retry_after == 0.0
