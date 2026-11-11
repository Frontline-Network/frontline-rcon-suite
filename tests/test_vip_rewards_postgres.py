"""Verify the shared lock against PostgreSQL; no game commands are executed."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from rcon import models
from rcon.vip_rewards import locking


@pytest.fixture
def postgres(monkeypatch):
    url = os.environ.get("VIP_REWARDS_TEST_DB_URL")
    if not url:
        pytest.skip("Explicit isolated PostgreSQL test database required")
    engine = create_engine(url, pool_size=3)
    monkeypatch.setattr(models, "get_engine", lambda: engine)
    yield engine
    engine.dispose()


def test_shared_lock_serializes_connections_and_releases_after_failure(postgres):
    key = "release-test:" + uuid4().hex
    waiting, entered = threading.Event(), threading.Event()

    def contender():
        waiting.set()
        with locking.lock(key):
            entered.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            with locking.lock(key):
                # Re-entrant callers do not consume another database connection.
                with locking.lock(key):
                    future = pool.submit(contender)
                    assert waiting.wait(5)
                    assert not entered.wait(0.3)
                    raise ValueError("simulated RCON failure")
        except ValueError:
            pass
        future.result(timeout=10)
        assert entered.is_set()


def test_busy_lock_times_out_without_entering_action(postgres, monkeypatch):
    key = "release-test:" + uuid4().hex

    def contender():
        ticks = iter((0, 16))
        monkeypatch.setattr(locking, "monotonic", lambda: next(ticks))
        with pytest.raises(TimeoutError, match="no action was attempted"):
            with locking.lock(key):
                pytest.fail("Busy VIP action must never execute")

    with ThreadPoolExecutor(max_workers=1) as pool:
        with locking.lock(key):
            pool.submit(contender).result(timeout=5)
