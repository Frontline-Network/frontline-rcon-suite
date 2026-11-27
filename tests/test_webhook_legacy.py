"""Legacy handoff failures against Lua-capable fake and real Redis."""

import os
import uuid

import pytest
import redis

from rcon import webhook_legacy as legacy


@pytest.fixture(params=["fake", "real"])
def red(request, monkeypatch):
    prefix = "webhook-legacy-test:" + uuid.uuid4().hex
    monkeypatch.setattr(legacy, "PREFIX", prefix)
    if request.param == "fake":
        fakeredis = pytest.importorskip("fakeredis")
        pytest.importorskip("lupa", reason="fakeredis Lua support is not installed")
        client = fakeredis.FakeRedis(decode_responses=False)
    else:
        url = os.getenv("TEST_REDIS_URL")
        if not url:
            pytest.skip("TEST_REDIS_URL not configured")
        client = redis.Redis.from_url(url, decode_responses=False)
        client.ping()
    yield client
    # Only the test's unique namespace is removed; never flush a shared DB.
    pending = []
    for key in client.scan_iter(match=prefix + ":*", count=100):
        pending.append(key)
        if len(pending) >= 100:
            client.delete(*pending)
            pending.clear()
    if pending:
        client.delete(*pending)
    client.close()


@pytest.fixture
def queue(red):
    return legacy.PREFIX + ":input"


def test_stage_keeps_original_head_until_sql_commit(red, queue):
    red.rpush(queue, b"first", b"second")
    stage = legacy.stage_next(red, queue)

    assert stage.raw == b"first"
    assert red.lrange(queue, 0, -1) == [b"first", b"second"]
    assert legacy.stage_next(red, queue) == stage
    assert red.ttl(legacy.stage_key(queue)) == -1
    assert legacy.staged_queues(red) == [queue]
    assert legacy.ack_stage(red, queue, stage.token) is True
    assert red.lrange(queue, 0, -1) == [b"second"]
    assert red.exists(legacy.stage_key(queue)) == 0
    assert legacy.staged_queues(red) == []


def test_two_importers_share_one_stage_and_stale_ack_cannot_pop_next(red, queue):
    red.rpush(queue, b"first", b"second")
    first = legacy.stage_next(red, queue)
    other = legacy.stage_next(red, queue)
    assert first == other
    assert legacy.ack_stage(red, queue, first.token) is True
    assert legacy.ack_stage(red, queue, other.token) is False
    assert red.lrange(queue, 0, -1) == [b"second"]


def test_identical_legitimate_payloads_get_distinct_import_tokens(red, queue):
    red.rpush(queue, b"same", b"same")
    first = legacy.stage_next(red, queue)
    assert legacy.ack_stage(red, queue, first.token)
    second = legacy.stage_next(red, queue)
    assert first.raw == second.raw
    assert first.token != second.token
    assert legacy.ack_stage(red, queue, second.token)
    assert red.llen(queue) == 0


def test_sql_failure_leaves_head_and_stage_available(red, queue):
    red.rpush(queue, b"important", b"next")
    stage = legacy.stage_next(red, queue)

    def fail(_stage):
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        legacy.import_queue(red, queue, fail)
    assert red.lrange(queue, 0, -1) == [b"important", b"next"]
    assert legacy.stage_next(red, queue) == stage


def test_crash_after_sql_commit_reuses_import_key_before_ack(red, queue):
    red.rpush(queue, b"first", b"second")
    committed = {}
    stage = legacy.stage_next(red, queue)
    committed["legacy:" + stage.token] = stage.raw
    # The first importer died after commit and never acknowledged Redis.
    calls = []

    def persist(recovered):
        calls.append(recovered)
        committed.setdefault("legacy:" + recovered.token, recovered.raw)

    assert legacy.import_queue(red, queue, persist, limit=1) == 1
    assert calls == [stage]
    assert len(committed) == 1
    assert red.lrange(queue, 0, -1) == [b"second"]


def test_binary_and_malformed_payloads_are_not_decoded_or_discarded(red, queue):
    raw = b'\xff\x00{"token":"do-not-log"'
    red.rpush(queue, raw)
    stage = legacy.stage_next(red, queue)
    assert stage.raw == raw
    assert "do-not-log" not in repr(stage)
    assert legacy.ack_stage(red, queue, stage.token)


def test_wrong_token_and_changed_head_never_remove_another_message(red, queue):
    red.rpush(queue, b"first", b"second")
    stage = legacy.stage_next(red, queue)
    assert legacy.ack_stage(red, queue, "wrong-owner") is False
    red.lset(queue, 0, b"externally changed")
    assert legacy.ack_stage(red, queue, stage.token) is False
    assert red.lrange(queue, 0, -1) == [b"externally changed", b"second"]
    assert legacy.stage_next(red, queue) == stage


def test_missing_queue_does_not_discard_a_recoverable_stage(red, queue):
    red.rpush(queue, b"important")
    stage = legacy.stage_next(red, queue)
    red.delete(queue)
    assert legacy.stage_next(red, queue) == stage
    assert legacy.ack_stage(red, queue, stage.token) is False
    assert legacy.staged_queues(red) == [queue]


@pytest.mark.parametrize("wrong_key", ["queue", "stage", "registry"])
def test_wrong_types_are_rejected_before_creating_stage(red, queue, wrong_key):
    red.rpush(queue, b"important")
    target = {"queue": queue, "stage": legacy.stage_key(queue), "registry": legacy.registry_key()}[wrong_key]
    red.delete(target)
    red.set(target, b"wrong type")
    with pytest.raises(redis.exceptions.ResponseError, match="wrong type"):
        legacy.stage_next(red, queue)
    assert red.get(target) == b"wrong type"
    if wrong_key != "queue":
        assert red.lrange(queue, 0, -1) == [b"important"]
    if wrong_key != "stage":
        assert not red.exists(legacy.stage_key(queue))


def test_wrong_registry_type_during_ack_cannot_pop_committed_head(red, queue):
    red.rpush(queue, b"important", b"next")
    stage = legacy.stage_next(red, queue)
    red.delete(legacy.registry_key())
    red.set(legacy.registry_key(), b"wrong type")
    with pytest.raises(redis.exceptions.ResponseError, match="wrong type"):
        legacy.ack_stage(red, queue, stage.token)
    assert red.lrange(queue, 0, -1) == [b"important", b"next"]
    assert red.exists(legacy.stage_key(queue))


def test_incomplete_stage_is_retained_and_reported(red, queue):
    red.rpush(queue, b"important")
    red.hset(legacy.stage_key(queue), mapping={"token": "incomplete"})
    with pytest.raises(redis.exceptions.ResponseError, match="incomplete"):
        legacy.stage_next(red, queue)
    with pytest.raises(redis.exceptions.ResponseError, match="incomplete"):
        legacy.ack_stage(red, queue, "incomplete")
    assert red.lrange(queue, 0, -1) == [b"important"]
    assert red.hgetall(legacy.stage_key(queue)) == {b"token": b"incomplete"}


def test_registry_can_be_repaired_without_changing_existing_stage(red, queue):
    red.rpush(queue, b"important")
    stage = legacy.stage_next(red, queue)
    red.delete(legacy.registry_key())
    assert legacy.stage_next(red, queue) == stage
    assert legacy.staged_queues(red) == [queue]


def test_import_batch_is_bounded_and_fifo(red, queue):
    values = [str(i).encode() for i in range(30)]
    red.rpush(queue, *values)
    saved = []
    assert legacy.import_queue(red, queue, lambda stage: saved.append(stage.raw), limit=20) == 20
    assert saved == values[:20]
    assert red.lrange(queue, 0, -1) == values[20:]


def test_discovery_is_bounded_and_empty_queue_creates_no_stage(red, queue):
    assert legacy.stage_next(red, queue) is None
    for i in range(7):
        key = queue + ":" + str(i)
        red.rpush(key, b"payload")
        legacy.stage_next(red, key)
    assert len(legacy.staged_queues(red, limit=3)) == 3
    assert legacy.staged_queues(red, limit=0) == []
    assert not legacy.registry_key().startswith("whs:")


def test_deleted_head_without_stage_clears_only_stale_registry_membership(red, queue):
    red.sadd(legacy.registry_key(), queue)
    assert legacy.stage_next(red, queue) is None
    assert legacy.staged_queues(red) == []
