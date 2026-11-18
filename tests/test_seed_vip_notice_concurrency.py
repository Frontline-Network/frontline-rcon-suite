import threading
import json
import os
from contextlib import nullcontext
from unittest.mock import Mock
from uuid import uuid4

import fakeredis
import pytest
import redis as redis_package

from rcon.seed_vip import notifications


def test_concurrent_consumers_send_a_notice_at_most_once(monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    redis = fakeredis.FakeStrictRedis()
    api = Mock()
    api.without_retries.side_effect = nullcontext
    api.message_player.return_value = True

    for index in range(20):
        redis.flushdb()
        api.message_player.reset_mock()
        queue = notifications.NotificationOutbox(redis, "test")
        queue.enqueue({f"fake-player-{index}": "fake notice"}, api)
        barrier = threading.Barrier(3)
        errors = []

        def consumer():
            try:
                barrier.wait()
                notifications.NotificationOutbox(redis, "test").flush(api)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=consumer) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        assert not errors
        api.message_player.assert_called_once_with(
            player_id=f"fake-player-{index}", message="fake notice"
        )


def test_clear_during_rejected_send_does_not_resurrect_notice(monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    redis = fakeredis.FakeStrictRedis()
    queue = notifications.NotificationOutbox(redis, "test")
    entered = threading.Event()
    resume = threading.Event()
    api = Mock()
    api.without_retries.side_effect = nullcontext

    def reject_after_clear(**_kwargs):
        entered.set()
        assert resume.wait(5)
        return False

    api.message_player.side_effect = reject_after_clear
    queue.enqueue({"synthetic-player": "synthetic notice"}, api)
    worker = threading.Thread(target=queue.flush, args=(api,))
    worker.start()
    try:
        assert entered.wait(5)
        queue.clear()
    finally:
        resume.set()
        worker.join(timeout=5)
    assert not worker.is_alive()
    assert redis.hlen(queue.key) == 0
    assert not redis.exists(queue.key)
    queue.flush(api)
    api.message_player.assert_called_once()


@pytest.fixture
def real_redis():
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("requires isolated Redis")
    client = redis_package.Redis.from_url(url)
    client.ping()
    yield client
    client.close()


def test_real_redis_clear_during_rejected_send_is_not_resurrected(real_redis, monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    queue = notifications.NotificationOutbox(real_redis, "isolated-" + uuid4().hex)
    entered, resume = threading.Event(), threading.Event()
    api = Mock()
    api.without_retries.side_effect = nullcontext

    def reject_after_clear(**_kwargs):
        entered.set()
        assert resume.wait(5)
        return False

    api.message_player.side_effect = reject_after_clear
    try:
        queue.enqueue({"synthetic-player": "synthetic notice"}, api)
        worker = threading.Thread(target=queue.flush, args=(api,))
        worker.start()
        try:
            assert entered.wait(5)
            queue.clear()
        finally:
            resume.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        assert real_redis.exists(queue.key) == 0
        assert queue.flush(api) is False
        api.message_player.assert_called_once()
    finally:
        queue.clear()


@pytest.mark.parametrize("replacement_mode", ["new_generation", "identical_aba"])
@pytest.mark.parametrize("accepted", [False, True])
def test_real_redis_replacement_during_watched_requeue_is_preserved(real_redis, monkeypatch, replacement_mode, accepted):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    watched_read, resume = threading.Event(), threading.Event()
    should_block = threading.Event()

    class WatchedPipeline:
        def __init__(self, inner):
            self.inner = inner

        def __enter__(self):
            self.inner.__enter__()
            return self

        def __exit__(self, *args):
            return self.inner.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def hget(self, *args):
            value = self.inner.hget(*args)
            if should_block.is_set():
                watched_read.set()
                assert resume.wait(5)
            return value

    class HookedRedis:
        def pipeline(self, **kwargs):
            return WatchedPipeline(real_redis.pipeline(**kwargs))

        def __getattr__(self, name):
            return getattr(real_redis, name)

    queue = notifications.NotificationOutbox(HookedRedis(), "isolated-" + uuid4().hex)
    api = Mock()
    api.without_retries.side_effect = nullcontext

    def reject(**_kwargs):
        should_block.set()
        return False

    api.message_player.side_effect = reject
    try:
        queue.enqueue({"synthetic-player": "old notice"}, api)
        ident = next(iter(real_redis.hgetall(queue.key)))
        worker = threading.Thread(target=queue.flush, args=(api,))
        worker.start()
        try:
            assert watched_read.wait(5)
            claimed = real_redis.hget(queue.key, ident)
            payload = json.loads(claimed)
            assert payload['claim_token']
            if replacement_mode == "new_generation":
                payload['claim_token'] = uuid4().hex
                replacement = json.dumps(payload).encode()
            else:
                # Even an exact delete/reinsert after WATCH must invalidate
                # the transaction, not restore the stale queued state.
                replacement = claimed
                real_redis.delete(queue.key)
            real_redis.hset(queue.key, ident, replacement)
            if replacement_mode == "identical_aba":
                real_redis.expire(queue.key, notifications.NOTICE_TTL)
        finally:
            resume.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        assert real_redis.hget(queue.key, ident) == replacement
        assert real_redis.ttl(queue.key) > 0
        api.message_player.assert_called_once()
    finally:
        queue.clear()


def test_real_redis_new_generation_before_requeue_is_preserved(real_redis, monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    queue = notifications.NotificationOutbox(real_redis, "isolated-" + uuid4().hex)
    entered, resume = threading.Event(), threading.Event()
    api = Mock()
    api.without_retries.side_effect = nullcontext

    def reject_after_replacement(**_kwargs):
        entered.set()
        assert resume.wait(5)
        return False

    api.message_player.side_effect = reject_after_replacement
    try:
        queue.enqueue({"synthetic-player": "same notice"}, api)
        ident = next(iter(real_redis.hgetall(queue.key)))
        worker = threading.Thread(target=queue.flush, args=(api,))
        worker.start()
        try:
            assert entered.wait(5)
            original = json.loads(real_redis.hget(queue.key, ident))
            assert original["claim_token"]
            replacement = {**original, "claim_token": uuid4().hex}
            assert {k: v for k, v in original.items() if k != "claim_token"} == {
                k: v for k, v in replacement.items() if k != "claim_token"}
            encoded = json.dumps(replacement).encode()
            real_redis.hset(queue.key, ident, encoded)
        finally:
            resume.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        assert real_redis.hget(queue.key, ident) == encoded
        assert real_redis.ttl(queue.key) > 0
        api.message_player.assert_called_once()
    finally:
        queue.clear()


def test_real_redis_ordinary_rejection_retains_ttl_and_retry(real_redis, monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    now = [1000]
    monkeypatch.setattr(notifications.time, "time", lambda: now[0])
    queue = notifications.NotificationOutbox(real_redis, "isolated-" + uuid4().hex)
    api = Mock()
    api.without_retries.side_effect = nullcontext
    api.message_player.side_effect = [False, True]
    try:
        queue.enqueue({"synthetic-player": "synthetic notice"}, api)
        assert queue.flush(api) is True
        assert real_redis.ttl(queue.key) > 0
        now[0] += notifications.RETRY_SECONDS
        assert queue.flush(api) is False
        assert api.message_player.call_count == 2
    finally:
        queue.clear()
