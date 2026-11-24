import os
import weakref
from datetime import datetime, timedelta
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

import rcon.models as models
from rcon import player_stats
from rcon.player_stats import _next_live_stats_sleep


def test_live_stats_sleeps_until_next_refresh_instead_of_polling():
    now = datetime(2026, 8, 17, 10, 0, 10)

    assert _next_live_stats_sleep(
        now=now,
        last_session_refresh=now - timedelta(seconds=5),
        last_game_refresh=now - timedelta(seconds=10),
        session_interval=15,
        game_interval=15,
    ) == 5


def test_live_stats_overdue_refresh_keeps_small_safety_floor():
    now = datetime(2026, 8, 17, 10, 0, 20)

    assert _next_live_stats_sleep(
        now=now,
        last_session_refresh=now - timedelta(seconds=20),
        last_game_refresh=now,
        session_interval=15,
        game_interval=15,
    ) == 0.1


def test_refresh_jobs_share_snapshot_and_release_it_before_sleep(monkeypatch):
    readers = []
    writes = []
    stop = Event()

    def record_reader(log_history):
        if readers:
            assert readers[0]() is log_history
        readers.append(weakref.ref(log_history))
        return {}

    def wait_once(timeout):
        stop.set()
        assert len(readers) == 2
        assert readers[0]() is None

    snapshot_class = player_stats.LogsHistorySnapshot
    monkeypatch.setattr(player_stats, "LogsHistorySnapshot", lambda: snapshot_class(history=[]))
    monkeypatch.setattr(player_stats, "LiveStats", lambda: SimpleNamespace(set_live_stats=record_reader))
    monkeypatch.setattr(player_stats, "current_game_stats", record_reader)
    monkeypatch.setattr(player_stats.RconServerSettingsUserConfig, "load_from_db",
                        lambda: SimpleNamespace(live_stats_refresh_seconds=15))
    monkeypatch.setattr(player_stats, "get_redis_client",
                        lambda: SimpleNamespace(set=lambda key, value: writes.append(key)))
    monkeypatch.setattr(stop, "wait", wait_once)
    player_stats.live_stats_loop(stop)
    assert writes == ["LIVE_GAME_STATS"]


def test_supervisor_engine_uses_bounded_connection_pool(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/crcon")
    monkeypatch.setenv("HLL_SUPERVISOR_PROCESS", "1")
    monkeypatch.delenv("HLL_DB_DISABLE_CONNECTION_POOL", raising=False)
    models._ENGINE = None

    sentinel = object()
    with patch.object(models, "create_engine", return_value=sentinel) as create_engine:
        assert models.get_engine() is sentinel

    options = create_engine.call_args.kwargs
    assert options["pool_size"] == 1
    assert options["max_overflow"] == 2
    assert options["pool_recycle"] == 900
    assert options["pool_use_lifo"] is True
    models._ENGINE = None


def test_explicit_null_pool_still_takes_precedence(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/crcon")
    monkeypatch.setenv("HLL_SUPERVISOR_PROCESS", "1")
    monkeypatch.setenv("HLL_DB_DISABLE_CONNECTION_POOL", "1")
    models._ENGINE = None

    sentinel = object()
    with patch.object(models, "create_engine", return_value=sentinel) as create_engine:
        assert models.get_engine() is sentinel

    options = create_engine.call_args.kwargs
    assert options["poolclass"] is models.NullPool
    assert "pool_size" not in options
    models._ENGINE = None
