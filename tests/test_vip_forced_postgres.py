"""Opt-in isolated PostgreSQL/Redis test for the forced-switch snapshot lock."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import os

import pytest
from redis import Redis
from sqlalchemy import create_engine

from rcon import models
from rcon.vip_rewards import hooks
from rcon.vip_rewards.locking import switch_state_lock


@pytest.mark.skipif(not os.environ.get("RCON_FORCE_TEST_DATABASE"), reason="requires isolated PostgreSQL and Redis")
def test_marker_creation_cannot_race_snapshot(monkeypatch):
    engine = create_engine(os.environ["RCON_FORCE_TEST_DATABASE"])
    redis = Redis.from_url(os.environ["RCON_FORCE_TEST_REDIS"], decode_responses=True)
    monkeypatch.setattr(models, "get_engine", lambda: engine)
    monkeypatch.setattr(hooks, "get_redis_client", lambda: redis)
    monkeypatch.setattr(hooks, "get_server_number", lambda: "isolated-lock-test")
    started, acquired, release = Event(), Event(), Event()

    def snapshot():
        with switch_state_lock():
            acquired.set()
            assert release.wait(5)
            assert not hooks.players_with_forced_switch(["test-player"], hooks.time.time())

    def start_switch():
        started.set()
        return hooks.mark_forced("test-player")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            worker = pool.submit(snapshot)
            assert acquired.wait(5)
            command = pool.submit(start_switch)
            assert started.wait(5)
            assert not command.done()
            release.set()
            worker.result(timeout=5)
            marker = command.result(timeout=5)
            with switch_state_lock():
                assert hooks.players_with_forced_switch(["test-player"], hooks.time.time()) == {"test-player"}
            hooks.finish_forced("test-player", marker, rejected=True)
    finally:
        release.set()
        engine.dispose()
