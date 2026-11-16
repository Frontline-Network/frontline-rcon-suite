"""An invalidated refresh must not restore its pre-change result."""
import os
import multiprocessing
from threading import Event, Thread

import pytest
import redis
from fakeredis import FakeServer, FakeStrictRedis

from rcon import cache_utils
from rcon.cache_utils import RedisCached


@pytest.fixture(params=["fake", "redis"])
def clients(request):
    if request.param == "redis":
        url = os.environ.get("TEST_REDIS_URL")
        if not url:
            pytest.skip("requires disposable Redis")
        first, second = redis.Redis.from_url(url), redis.Redis.from_url(url)
        first.flushdb()
    else:
        server = FakeServer()
        first, second = FakeStrictRedis(server=server), FakeStrictRedis(server=server)
    yield first, second
    first.flushdb()
    first.close()
    second.close()


@pytest.mark.parametrize("invalidation", ["one", "function", "global", "restart"])
@pytest.mark.parametrize("stale", [False, True])
def test_invalidated_inflight_refresh_cannot_repopulate_cache(clients, monkeypatch, invalidation, stale):
    first, second = clients
    began, release, finished = Event(), Event(), Event()
    state = {"value": "old"}
    def read():
        value = state["value"]
        if not began.is_set():
            began.set()
            assert release.wait(5)
        return value
    cached = RedisCached(None, 60, read, red=first)
    invalidator = RedisCached(None, 60, read, red=second)
    if stale:
        first.setex(cached.stale_key(cached.key()), 60, '"prior"')
        original_release = cached._release_lock
        def release_lock(*args):
            try:
                original_release(*args)
            finally:
                finished.set()
        monkeypatch.setattr(cached, "_release_lock", release_lock)
        assert cached() == "prior"
        thread = None
    else:
        def run():
            try:
                cached()
            finally:
                finished.set()
        thread = Thread(target=run)
        thread.start()
    try:
        assert began.wait(5)
        state["value"] = "new"
        if invalidation == "one":
            invalidator.clear_for()
        elif invalidation == "function":
            invalidator.clear_all()
        elif invalidation == "global":
            monkeypatch.setattr(cache_utils.redis, "Redis", lambda **_kwargs: second)
            RedisCached.clear_all_caches(None)
        else:
            second.flushdb()  # A disposable database represents a Redis restart.
        release.set()
        assert finished.wait(5)
        assert first.get(cached.key()) is None
        assert first.get(cached.stale_key(cached.key())) is None
        assert cached() == "new"
    finally:
        release.set()
        if thread is not None:
            thread.join(timeout=5)


def test_invalidation_crosses_process_boundaries():
    url = os.environ.get("TEST_REDIS_URL")
    if not url or "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("requires disposable Redis and fork")
    context = multiprocessing.get_context("fork")
    began, release = context.Event(), context.Event()
    red = redis.Redis.from_url(url)
    red.flushdb()
    def read():
        began.set()
        assert release.wait(5)
        return "old"
    def worker():
        client = redis.Redis.from_url(url)
        try:
            RedisCached(None, 60, read, red=client)()
        finally:
            client.close()
    process = context.Process(target=worker)
    process.start()
    try:
        assert began.wait(5)
        invalidator = RedisCached(None, 60, read, red=red)
        invalidator.clear_for()
        release.set()
        process.join(5)
        assert process.exitcode == 0
        assert red.get(invalidator.key()) is None
        assert red.get(invalidator.stale_key(invalidator.key())) is None
    finally:
        release.set()
        if process.is_alive():
            process.terminate()
            process.join(5)
        red.flushdb()
        red.close()
