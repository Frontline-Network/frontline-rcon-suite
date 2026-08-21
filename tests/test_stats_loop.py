import socket
from unittest.mock import Mock

from rcon.stats_loop import Series


class _ExampleSeries(Series):
    NAME = "test_series"

    def snapshot(self, rcon):
        self.snapshot_impl(rcon)


def _series(snapshot_impl, clock):
    series = _ExampleSeries(client=Mock(), min_resolution_ms=0, clock=clock)
    series.snapshot_impl = snapshot_impl
    return series


def test_expected_snapshot_error_is_degraded_and_backed_off():
    snapshot = Mock(side_effect=socket.timeout("timed out"))
    series = _series(snapshot, Mock(side_effect=[100.0, 100.5, 101.0]))

    assert series.run_on_time(Mock()) is None
    assert series.health() == {
        "name": "test_series",
        "degraded": True,
        "consecutive_failures": 1,
        "last_error": "TimeoutError: timed out",
        "last_error_at": 100.0,
        "next_retry_at": 101.0,
        "last_success_at": None,
    }

    # Polling is still active, but no second failing RCON request is sent before retry.
    assert series.run_on_time(Mock()) is None
    snapshot.assert_called_once()

    assert series.run_on_time(Mock()) is None
    assert snapshot.call_count == 2


def test_success_clears_degraded_health():
    snapshot = Mock(side_effect=[socket.timeout("timed out"), None])
    series = _series(snapshot, Mock(side_effect=[100.0, 101.0]))

    series.run_on_time(Mock())
    assert series.run_on_time(Mock()) == 101.0

    health = series.health()
    assert health["degraded"] is False
    assert health["consecutive_failures"] == 0
    assert health["last_error"] is None
    assert health["last_success_at"] == 101.0
