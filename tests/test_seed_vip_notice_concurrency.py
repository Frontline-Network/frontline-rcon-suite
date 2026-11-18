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


class FakeRedisWithCompletion(fakeredis.FakeStrictRedis):
    """Test double for fake Redis installations without the Lua extra."""

    def eval(self, script, key_count, key, field, expected, action, queued):
        assert script == notifications.COMPLETE_CLAIM and key_count == 1
        if self.hget(key, field) != expected.encode():
            return 0
        if action == 'delete':
            self.hdel(key, field)
        else:
            self.hset(key, field, queued)
        return 1


def test_concurrent_consumers_send_a_notice_at_most_once(monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    redis = FakeRedisWithCompletion()
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
    redis = FakeRedisWithCompletion()
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


@pytest.mark.parametrize("mode", ["new_generation", "unrelated", "clear"])
@pytest.mark.parametrize("accepted", [False, True])
def test_real_redis_atomic_completion_handles_concurrent_changes(real_redis, monkeypatch, mode, accepted):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    entered, resume = threading.Event(), threading.Event()

    class HookedRedis:
        def eval(self, *args):
            entered.set()
            assert resume.wait(5)
            return real_redis.eval(*args)

        def __getattr__(self, name):
            return getattr(real_redis, name)

    queue = notifications.NotificationOutbox(HookedRedis(), "isolated-" + uuid4().hex)
    api = Mock()
    api.without_retries.side_effect = nullcontext
    api.message_player.return_value = accepted
    try:
        queue.enqueue({"synthetic-player": "notice"}, api)
        ident = next(iter(real_redis.hgetall(queue.key)))
        worker = threading.Thread(target=queue.flush, args=(api,))
        worker.start()
        try:
            assert entered.wait(5)
            claimed = json.loads(real_redis.hget(queue.key, ident))
            assert claimed["claim_token"]
            if mode == "new_generation":
                replacement = {**claimed, "claim_token": uuid4().hex}
                encoded = json.dumps(replacement).encode()
                real_redis.hset(queue.key, ident, encoded)
            elif mode == "unrelated":
                real_redis.hset(queue.key, "other", "unrelated")
            else:
                real_redis.delete(queue.key)
        finally:
            resume.set()
            worker.join(timeout=5)
        assert not worker.is_alive()
        api.message_player.assert_called_once()
        if mode == "new_generation":
            assert real_redis.hget(queue.key, ident) == encoded
            assert real_redis.ttl(queue.key) > 0
        elif mode == "clear":
            assert not real_redis.exists(queue.key)
        else:
            assert real_redis.hget(queue.key, "other") == b"unrelated"
            assert real_redis.ttl(queue.key) > 0
            actual = real_redis.hget(queue.key, ident)
            if accepted:
                assert actual is None
            else:
                queued = json.loads(actual)
                assert queued["state"] == "queued"
                assert "claim_token" not in queued
    finally:
        queue.clear()

@pytest.mark.parametrize("execute_first", [False, True])
@pytest.mark.parametrize("accepted", [False, True])
def test_real_redis_completion_reply_loss_does_not_duplicate(real_redis, monkeypatch, execute_first, accepted):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)

    class FailingRedis:
        fail = True

        def eval(self, *args):
            if self.fail:
                self.fail = False
                if execute_first:
                    real_redis.eval(*args)
                raise redis_package.ConnectionError("synthetic lost response")
            return real_redis.eval(*args)

        def __getattr__(self, name):
            return getattr(real_redis, name)

    queue = notifications.NotificationOutbox(FailingRedis(), "isolated-" + uuid4().hex)
    api = Mock()
    api.without_retries.side_effect = nullcontext
    api.message_player.return_value = accepted
    try:
        queue.enqueue({"synthetic-player": "notice"}, api)
        queue.flush(api)
        queue.flush(api)
        api.message_player.assert_called_once()
        values = list(real_redis.hgetall(queue.key).values())
        if execute_first and accepted:
            assert not values
        else:
            assert len(values) == 1
            item = json.loads(values[0])
            assert item['state'] == ('queued' if execute_first else 'sending')
            assert real_redis.ttl(queue.key) > 0
    finally:
        queue.clear()


def test_real_redis_simultaneous_completion_only_one_wins(real_redis):
    key = "seed-test:" + uuid4().hex
    try:
        for _ in range(50):
            original = json.dumps({"state": "sending", "claim_token": uuid4().hex})
            real_redis.hset(key, "same", original)
            real_redis.expire(key, 120)
            barrier = threading.Barrier(3)
            results = []

            def complete(action):
                barrier.wait()
                results.append(real_redis.eval(notifications.COMPLETE_CLAIM, 1,
                                               key, "same", original, action, '{"state":"queued"}'))

            workers = [threading.Thread(target=complete, args=(action,)) for action in ("delete", "requeue")]
            for worker in workers:
                worker.start()
            barrier.wait()
            for worker in workers:
                worker.join(timeout=5)
                assert not worker.is_alive()
            assert sorted(results) == [0, 1]
            if real_redis.exists(key):
                assert real_redis.ttl(key) > 0
    finally:
        real_redis.delete(key)


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
