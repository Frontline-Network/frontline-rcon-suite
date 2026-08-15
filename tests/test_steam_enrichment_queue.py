from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from rcon import hooks


def _connection_log(event_time: datetime) -> dict:
    return {
        "event_time": event_time,
        "timestamp_ms": int(event_time.timestamp() * 1000),
        "player_name_1": "Test Player",
        "player_id_1": "76561198000000000",
    }


def _patch_queue_dependencies(monkeypatch, *, marker_created: bool = True):
    red = Mock()
    red.set.return_value = marker_created
    queue = Mock()
    monkeypatch.setattr(hooks, "get_redis_client", lambda: red)
    monkeypatch.setattr(hooks, "get_queue", lambda: queue)
    monkeypatch.setattr(hooks, "get_server_number", lambda: 2)
    return red, queue


def test_historical_connections_do_not_queue_steam_enrichment(monkeypatch):
    red, queue = _patch_queue_dependencies(monkeypatch)
    log = _connection_log(datetime.now(tz=UTC) - timedelta(minutes=6))

    hooks.update_player_steaminfo_on_connect(None, log)

    red.set.assert_not_called()
    queue.enqueue.assert_not_called()


def test_recent_connection_queues_one_deduplicated_enrichment(monkeypatch):
    red, queue = _patch_queue_dependencies(monkeypatch)
    log = _connection_log(datetime.now(tz=UTC) - timedelta(seconds=5))

    hooks.update_player_steaminfo_on_connect(None, log)

    red.set.assert_called_once_with(
        "steam_connect_enrichment:2:76561198000000000",
        "1",
        nx=True,
        ex=hooks.STEAM_ENRICHMENT_DEDUPE_SECONDS,
    )
    queue.enqueue.assert_called_once_with(
        hooks.update_player_steaminfo_on_connect_worker,
        "Test Player",
        "76561198000000000",
        job_timeout=60,
    )


def test_recent_duplicate_connection_does_not_queue_again(monkeypatch):
    _, queue = _patch_queue_dependencies(monkeypatch, marker_created=False)
    log = _connection_log(datetime.now(tz=UTC) - timedelta(seconds=5))

    hooks.update_player_steaminfo_on_connect(None, log)

    queue.enqueue.assert_not_called()


def test_failed_enqueue_releases_dedupe_marker(monkeypatch):
    red, queue = _patch_queue_dependencies(monkeypatch)
    queue.enqueue.side_effect = RuntimeError("queue unavailable")
    log = _connection_log(datetime.now(tz=UTC) - timedelta(seconds=5))

    with pytest.raises(RuntimeError, match="queue unavailable"):
        hooks.update_player_steaminfo_on_connect(None, log)

    red.delete.assert_called_once_with("steam_connect_enrichment:2:76561198000000000")
