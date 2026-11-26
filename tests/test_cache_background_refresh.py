"""Slow cache refreshes must have bounded lifetime, concurrency and owned leases."""
import threading
import time
import multiprocessing
import os
from unittest import mock

import pytest
import redis
from fakeredis import FakeStrictRedis

from rcon import cache_utils
from rcon.cache_utils import BackgroundRefreshCoordinator, RedisCached
from tests.test_cache_refresh_generation import clients


def until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate()


@pytest.fixture
def coordinator(monkeypatch):
    result = BackgroundRefreshCoordinator(max_workers=2, renew_interval=0.03)
    monkeypatch.setattr(cache_utils, "_BACKGROUND_REFRESHES", result)
    monkeypatch.setattr(cache_utils, "CACHE_REFRESH_LEASE_SECONDS", 1)
    yield result
    result.close()
    until(lambda: not result._active)


def seed_stale(cached, *args):
    cached.red.setex(cached.stale_key(cached.key(*args)), 6, '"prior"')


def test_slow_refresh_keeps_lease_across_its_original_ttl(clients, coordinator):
    first, second = clients
    began, release = threading.Event(), threading.Event()
    read = mock.Mock()
    def slow():
        read()
        began.set()
        assert release.wait(5)
        return "new"
    cached = RedisCached(None, 1, slow, red=first)
    other_pool = RedisCached(None, 1, slow, red=second)
    seed_stale(cached)
    try:
        assert cached() == "prior"
        assert began.wait(2)
        token = first.get(cached.lock_key(cached.key()))
        time.sleep(1.15)
        assert first.get(cached.lock_key(cached.key())) == token
        assert other_pool() == "prior"
        read.assert_called_once()
    finally:
        release.set()
    until(lambda: not coordinator._active)
    assert cached() == "new"
    read.assert_called_once()


def test_same_pool_does_not_duplicate_refresh_after_lease_loss(coordinator):
    red = FakeStrictRedis()
    began, release = threading.Event(), threading.Event()
    reads = mock.Mock()
    def slow():
        reads()
        began.set()
        assert release.wait(3)
        return "obsolete"
    cached = RedisCached(None, 1, slow, red=red)
    seed_stale(cached)
    try:
        assert cached() == "prior"
        assert began.wait(2)
        red.delete(cached.lock_key(cached.key()))
        assert cached() == "prior"
        reads.assert_called_once()
    finally:
        release.set()
    until(lambda: not coordinator._active)
    assert red.get(cached.key()) is None
    assert red.get(cached.stale_key(cached.key())) == b'"prior"'


def test_distinct_keys_are_bounded_without_an_executor_queue(coordinator):
    red = FakeStrictRedis()
    release = threading.Event()
    reads = mock.Mock()
    def slow(number):
        reads(number)
        assert release.wait(3)
        return number
    cached = RedisCached(None, 1, slow, red=red)
    for number in range(8):
        seed_stale(cached, number)
    try:
        started = time.monotonic()
        assert [cached(number) for number in range(8)] == ["prior"] * 8
        assert time.monotonic() - started < 1
        until(lambda: reads.call_count == 2)
        assert len(coordinator._active) == 2
        assert coordinator._keeper.daemon
        assert all(t.daemon for t in threading.enumerate() if t.name.startswith("cache-refresh-"))
        assert all(red.get(cached.lock_key(cached.key(number))) is None for number in range(2,8))
        with mock.patch.object(red, "set", side_effect=AssertionError("overload must not acquire another lease")):
            assert cached(7) == "prior"
    finally:
        release.set()
    until(lambda: not coordinator._active)
    assert reads.call_count == 2  # Rejected jobs were not queued for later.
    assert cached(2) == "prior"
    until(lambda: reads.call_count == 3 and not coordinator._active)


def test_equal_keys_in_other_redis_pools_have_independent_capacity(coordinator):
    release = threading.Event()
    reads = mock.Mock()
    def slow():
        reads()
        assert release.wait(3)
        return "new"
    left = RedisCached(None, 1, slow, red=FakeStrictRedis())
    right = RedisCached(None, 1, slow, red=FakeStrictRedis())
    seed_stale(left)
    seed_stale(right)
    try:
        assert left() == right() == "prior"
        until(lambda: reads.call_count == 2)
        assert len(coordinator._active) == 2
    finally:
        release.set()


def test_refresh_exception_releases_capacity_and_owned_lock(coordinator):
    red = FakeStrictRedis()
    attempts = []
    def read():
        attempts.append(True)
        raise ValueError("synthetic refresh failure")
    cached = RedisCached(None, 1, read, red=red)
    seed_stale(cached)
    assert cached() == "prior"
    until(lambda: attempts and not coordinator._active)
    assert red.get(cached.lock_key(cached.key())) is None
    assert cached() == "prior"
    until(lambda: len(attempts) == 2 and not coordinator._active)


@pytest.mark.parametrize("fail_start", ["keeper", "worker"])
def test_thread_start_failure_releases_slot_and_lease(coordinator, fail_start):
    red = FakeStrictRedis()
    read = mock.Mock(return_value="new")
    read.__name__ = read.__qualname__ = "start_failure"
    cached = RedisCached(None, 1, read, red=red)
    seed_stale(cached)
    original = threading.Thread.start
    def start(thread):
        if (thread.name == "cache-refresh-leases") == (fail_start == "keeper"):
            raise RuntimeError("synthetic interpreter shutdown")
        return original(thread)
    with mock.patch.object(threading.Thread, "start", start):
        assert cached() == "prior"
    assert not coordinator._active
    assert red.get(cached.lock_key(cached.key())) is None
    read.assert_not_called()
    assert cached() == "prior"
    until(lambda: read.called and not coordinator._active)


def test_shutdown_rejects_new_jobs_without_releasing_an_active_lease(coordinator):
    red = FakeStrictRedis()
    began, release = threading.Event(), threading.Event()
    reads = mock.Mock()
    def slow(number):
        reads(number)
        began.set()
        assert release.wait(4)
        return number
    cached = RedisCached(None, 1, slow, red=red)
    seed_stale(cached, 1)
    seed_stale(cached, 2)
    try:
        assert cached(1) == "prior"
        assert began.wait(2)
        token = red.get(cached.lock_key(cached.key(1)))
        coordinator.close()
        time.sleep(1.15)
        assert red.get(cached.lock_key(cached.key(1))) == token
        assert cached(2) == "prior"
        assert red.get(cached.lock_key(cached.key(2))) is None
        reads.assert_called_once_with(1)
    finally:
        release.set()
    until(lambda: not coordinator._active)
    assert red.get(cached.lock_key(cached.key(1))) is None


def test_lost_owner_cannot_publish_or_release_a_replacement_token(clients, coordinator):
    first, second = clients
    began, release = threading.Event(), threading.Event()
    def slow():
        began.set()
        assert release.wait(3)
        return "obsolete"
    cached = RedisCached(None, 1, slow, red=first)
    seed_stale(cached)
    try:
        assert cached() == "prior"
        assert began.wait(2)
        second.set(cached.lock_key(cached.key()), "replacement", ex=10)
        second.setex(cached.key(), 10, '"newer"')
    finally:
        release.set()
    until(lambda: not coordinator._active)
    assert first.get(cached.key()) == b'"newer"'
    assert first.get(cached.lock_key(cached.key())) == b"replacement"


def test_renewal_redis_error_does_not_delete_or_replace_the_lock(coordinator):
    red = FakeStrictRedis()
    cached = RedisCached(None, 1, lambda: None, red=red)
    key = cached.lock_key(cached.key())
    red.setex(key, 10, "owner")
    with mock.patch.object(red, "pipeline", side_effect=redis.exceptions.RedisError("synthetic outage")):
        assert cached._renew_lock(key, "owner") is None
    assert red.get(key) == b"owner"
    assert cached._renew_lock(key, "other") is False
    assert red.get(key) == b"owner"


def test_release_error_does_not_leak_a_process_slot(coordinator, monkeypatch):
    red = FakeStrictRedis()
    def read():
        return "new"
    cached = RedisCached(None, 1, read, red=red)
    seed_stale(cached)
    monkeypatch.setattr(cached, "_release_lock", mock.Mock(side_effect=redis.exceptions.RedisError("outage")))
    assert cached() == "prior"
    until(lambda: not coordinator._active)


def test_publication_is_serialized_with_renewal_but_the_read_is_not(coordinator, monkeypatch):
    red = FakeStrictRedis()
    def read():
        job = next(iter(coordinator._active.values()))
        assert not job.lease_mutex.locked()
        return "new"
    cached = RedisCached(None, 1, read, red=red)
    original = cached._store_cached_value
    def publish(*args, **kwargs):
        job = next(iter(coordinator._active.values()))
        assert job.lease_mutex.locked()
        return original(*args, **kwargs)
    monkeypatch.setattr(cached, "_store_cached_value", publish)
    seed_stale(cached)
    assert cached() == "prior"
    until(lambda: not coordinator._active)
    assert red.get(cached.key()) == b'"new"'


def test_fork_reset_discards_parent_state_without_releasing_parent_tokens(coordinator):
    old_mutex = coordinator._mutex
    release = mock.Mock()
    coordinator._active["parent-only"] = mock.Mock(release=release)
    coordinator.after_fork()
    assert coordinator._mutex is not old_mutex
    assert not coordinator._active and coordinator._keeper is None
    release.assert_not_called()


def test_renewed_refresh_lease_is_shared_across_processes(coordinator):
    url = os.environ.get("TEST_REDIS_URL")
    if not url or "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("requires disposable Redis and fork")
    context = multiprocessing.get_context("fork")
    began, release = context.Event(), context.Event()
    red = redis.Redis.from_url(url)
    red.flushdb()
    parent_read = mock.Mock(return_value="duplicate")
    parent_read.__name__ = parent_read.__qualname__ = "cross_process_refresh"
    cached = RedisCached(None, 1, parent_read, red=red)
    seed_stale(cached)
    def worker():
        client = redis.Redis.from_url(url)
        def read():
            began.set()
            assert release.wait(5)
            return "new"
        read.__name__ = read.__qualname__ = "cross_process_refresh"
        try:
            assert RedisCached(None, 1, read, red=client)() == "prior"
            assert release.wait(5)
            until(lambda: not cache_utils._BACKGROUND_REFRESHES._active)
            cache_utils._BACKGROUND_REFRESHES.close()
        finally:
            client.close()
    process = context.Process(target=worker)
    process.start()
    try:
        assert began.wait(2)
        token = red.get(cached.lock_key(cached.key()))
        time.sleep(1.15)
        assert red.get(cached.lock_key(cached.key())) == token
        assert cached() == "prior"
        parent_read.assert_not_called()
        release.set()
        process.join(3)
        assert process.exitcode == 0
        assert red.get(cached.key()) == b'"new"'
    finally:
        release.set()
        if process.is_alive():
            process.terminate()
            process.join(3)
        red.flushdb()
        red.close()
