import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

from fakeredis import FakeStrictRedis
import orjson
import httpx
import pytest
import redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from rcon.webhook_service import (
    WebhookQueueKeyCache,
    DEAD_LETTER_QUEUE,
    DeadLetterWebhookMessage,
    EMPTY_DEQUEUE_COUNT,
    RATE_LIMIT_LOCK_METRICS_TTL_SECS,
    RATE_LIMIT_LOCK_WAIT_COUNT,
    RATE_LIMIT_LOCK_WAIT_MS,
    DiscordRateLimitData,
    WebhookMessage,
    WebhookMessageType,
    WebhookType,
    dequeue_message,
    enqueue_message,
    enqueue_transient_message,
    get_queue_registry_key,
    handle_webhook_not_found,
    get_dead_letter_messages,
    get_bucket_lock,
    get_or_create_bucket_lock,
    move_to_dead_letter,
    retry_dead_letter_message,
    record_bucket_lock_wait,
    set_bucket_data,
)
from rcon import webhook_outbox as outbox, webhook_service


@pytest.fixture(autouse=True)
def outbox_database(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "webhook-service.sqlite"),
                           connect_args={"check_same_thread": False})
    outbox.WebhookOutboxQueue.__table__.create(engine)
    outbox.WebhookOutboxDelivery.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(outbox, "get_session_maker", lambda: maker)
    monkeypatch.setattr(webhook_service, "get_server_number", lambda: "1")
    monkeypatch.setattr(webhook_service, "WH_MAX_QUEUE_LENGTH", 150)
    monkeypatch.setattr(webhook_service, "WH_MAX_MESSAGE_AGE_SECS", 3600)
    monkeypatch.setattr(webhook_service, "_next_wakeup_attempt_at", 0.0)
    # These are SQL delivery/metadata unit tests. Native Lua handoff is covered
    # by test_webhook_legacy and the real-Redis durable-delivery integration run.
    monkeypatch.setattr(webhook_service, "_import_legacy_queue", lambda *a, **kw: 0)
    monkeypatch.setattr(webhook_service, "_import_legacy_dead_letters", lambda *a, **kw: 0)
    webhook_service._RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(webhook_service, "_SHARED_LOCK", None)
    try:
        yield maker
    finally:
        webhook_service._RATE_LIMIT_BUCKETS.clear()
        engine.dispose()


def _stored_rows(maker):
    with maker() as session:
        return list(session.scalars(select(outbox.WebhookOutboxDelivery).order_by(
            outbox.WebhookOutboxDelivery.id)))


def _message(message_type=WebhookMessageType.AUDIT):
    return WebhookMessage(
        server_number=1,
        webhook_type=WebhookType.DISCORD,
        message_type=message_type,
        payload={
            "url": "https://discord.com/api/webhooks/123/token",
            "webhook_id": "123",
            "webhook_token": "token",
            "content": "test",
            "rate_limit_retry": False,
        },
    )


def test_enqueue_logs_do_not_expose_webhook_credentials(caplog):
    import logging
    red = Mock()
    red.pipeline.return_value = Mock()
    message = _message()
    with caplog.at_level(logging.DEBUG, logger=webhook_service.__name__):
        enqueue_message(message, red=red)
        enqueue_transient_message(message, message_group_key="score", red=red)
    assert "discord.com/api/webhooks/123/token" not in caplog.text
    assert "webhook_token" not in caplog.text


@pytest.mark.parametrize("failure", [400, 502, "transport"])
def test_delivery_failure_logs_do_not_expose_webhook_payload(monkeypatch, caplog, failure):
    import logging
    from types import SimpleNamespace

    secret = "fake-webhook-secret"
    message = _message().model_copy(update={"payload": {
        **_message().payload, "url": "https://example.invalid/" + secret,
        "webhook_token": secret, "content": secret,
    }})
    red = FakeStrictRedis()
    enqueue_message(message, red=red)
    wh = SimpleNamespace(webhook_id="123", url="https://example.invalid/" + secret,
                         execute=AsyncMock())
    if failure == "transport":
        wh.execute.side_effect = httpx.ConnectError(secret)
    else:
        wh.execute.return_value = SimpleNamespace(status_code=failure, headers={"secret": secret})
    monkeypatch.setattr(webhook_service, "construct_webhook", lambda **_: wh)
    with caplog.at_level(logging.DEBUG, logger=webhook_service.__name__):
        asyncio.run(dequeue_message(red=red, client=Mock(), queue_id="whs:1:discord:audit:123",
                                    bucket_data=None, lock=asyncio.Lock()))
    assert secret not in caplog.text
    assert outbox.summary() == {"review": 1}


def test_global_rate_limit_does_not_log_untrusted_response(monkeypatch, caplog):
    import logging
    from types import SimpleNamespace

    secret = "fake-response-secret"
    message = _message()
    red = FakeStrictRedis()
    enqueue_message(message, red=red)
    response = SimpleNamespace(
        status_code=429,
        headers={"x-ratelimit-bucket": "", "x-ratelimit-remaining": "0", "x-ratelimit-reset-after": "1"},
        json=lambda: {"global": True, "retry_after": secret, "message": secret},
    )
    wh = SimpleNamespace(webhook_id="123", execute=AsyncMock(return_value=response))
    monkeypatch.setattr(webhook_service, "construct_webhook", lambda **_: wh)
    monkeypatch.setattr(webhook_service, "update_bucket_rate_limit", Mock())
    monkeypatch.setattr(webhook_service, "set_global_rate_limit_reset_after", Mock())
    with caplog.at_level(logging.DEBUG, logger=webhook_service.__name__):
        asyncio.run(dequeue_message(red=red, client=Mock(), queue_id="whs:1:discord:audit:123",
                                    bucket_data=None, lock=asyncio.Lock()))
    assert secret not in caplog.text
    webhook_service.set_global_rate_limit_reset_after.assert_called_once()
    assert outbox.summary() == {"queued": 1}


def test_queue_registry_is_installation_wide():
    assert get_queue_registry_key(prefix="whs") == "whs:queue_registry"


def test_known_and_late_discovered_webhooks_share_one_bucket_lock():
    webhook_service._RATE_LIMIT_BUCKETS.clear()
    red = Mock()
    red.get.return_value = None

    _, first_lock = get_bucket_lock(red=red, bucket_id="discord-shared")
    discovered_lock = get_or_create_bucket_lock(bucket_id="discord-shared")
    set_bucket_data(
        red=red,
        bucket=DiscordRateLimitData(id="discord-shared"),
        lock=discovered_lock,
    )
    _, late_lock = get_bucket_lock(red=red, bucket_id="discord-shared")

    assert first_lock is discovered_lock is late_lock


def test_contended_bucket_lock_wait_is_recorded_as_expiring_metrics():
    red = Mock()
    pipe = Mock()
    red.pipeline.return_value = pipe

    record_bucket_lock_wait(
        red=red,
        bucket_id="discord-shared",
        wait_seconds=0.042,
    )

    pipe.hincrby.assert_any_call(RATE_LIMIT_LOCK_WAIT_MS, "discord-shared", 42)
    pipe.hincrby.assert_any_call(RATE_LIMIT_LOCK_WAIT_COUNT, "discord-shared", 1)
    pipe.expire.assert_any_call(
        RATE_LIMIT_LOCK_WAIT_MS, RATE_LIMIT_LOCK_METRICS_TTL_SECS
    )
    pipe.expire.assert_any_call(
        RATE_LIMIT_LOCK_WAIT_COUNT, RATE_LIMIT_LOCK_METRICS_TTL_SECS
    )
    pipe.execute.assert_called_once()


def test_uncontended_bucket_lock_wait_does_not_write_metrics():
    red = Mock()

    record_bucket_lock_wait(red=red, bucket_id="discord-shared", wait_seconds=0)

    red.pipeline.assert_not_called()


def test_webhook_404_without_message_id_marks_error_and_retains_queued_payloads(outbox_database):
    red = FakeStrictRedis()
    queued = enqueue_message(_message(), red=red)
    legacy = orjson.dumps(_message().model_dump_json())
    red.rpush("whs:1:discord:audit:123", legacy)

    handle_webhook_not_found(
        red=red,
        queue_id="whs:1:discord:audit:123",
        payload={"webhook_id": "123"},
        webhook_type=WebhookType.DISCORD,
        webhook_id="123",
    )

    assert red.lrange("whs:1:discord:audit:123", 0, -1) == [legacy]
    assert outbox.lookup(queued)["status"] == "queued"
    assert _stored_rows(outbox_database)[0].payload
    assert webhook_service.get_webhook_error(red, "123", WebhookType.DISCORD)["http_404"] is True


def test_webhook_404_with_message_id_marks_edit_without_deleting_related_payloads(outbox_database):
    red = FakeStrictRedis()
    message = _message(WebhookMessageType.SCOREBOARD)
    message.payload["message_id"] = "456"
    queued = enqueue_message(message, red=red)
    legacy = orjson.dumps(message.model_dump_json())
    red.rpush("whs:1:discord:scoreboard:123", legacy)

    handle_webhook_not_found(
        red=red,
        queue_id="whs:1:discord:scoreboard:123",
        payload={"webhook_id": "123", "message_id": "456"},
        webhook_type=WebhookType.DISCORD,
        webhook_id="123",
    )

    assert webhook_service.get_message_edit_404_failure("456", red=red) is True
    assert red.lrange("whs:1:discord:scoreboard:123", 0, -1) == [legacy]
    assert outbox.lookup(queued)["status"] == "queued"
    assert _stored_rows(outbox_database)[0].payload
    assert webhook_service.get_webhook_error(red, "123", WebhookType.DISCORD)["http_404"] is True


def test_enqueue_persists_payload_before_indexing_only_a_bounded_wakeup(outbox_database):
    red = Mock()
    pipe = red.pipeline.return_value

    delivery_id = enqueue_message(_message(), red=red)

    pipe.rpush.assert_called_once_with(webhook_service.OUTBOX_WAKEUPS_KEY, delivery_id)
    pipe.ltrim.assert_called_once_with(webhook_service.OUTBOX_WAKEUPS_KEY, -150, -1)
    pipe.sadd.assert_not_called()
    pipe.execute.assert_called_once_with()
    stored = _stored_rows(outbox_database)
    assert len(stored) == 1 and stored[0].message_id == delivery_id and stored[0].status == "queued"
    assert webhook_service.unpack_message(stored[0].payload).payload == _message().payload


def test_wakeup_circuit_preserves_sql_messages_without_repeated_redis_attempts(monkeypatch, outbox_database):
    from types import SimpleNamespace

    clock = [100.0]
    monkeypatch.setattr(webhook_service, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    red = Mock()
    pipe = red.pipeline.return_value
    pipe.execute.side_effect = redis.exceptions.ConnectionError("synthetic Redis interruption")
    enqueue_message(_message(), red=red)
    for _ in range(100):
        enqueue_message(_message(), red=red)
    assert red.pipeline.call_count == 1
    assert outbox.summary() == {"queued": 101}
    assert all(row.payload for row in _stored_rows(outbox_database))

    clock[0] += 1.1
    pipe.execute.side_effect = None
    recovered = enqueue_message(_message(), red=red)
    assert red.pipeline.call_count == 2
    pipe.rpush.assert_called_with(webhook_service.OUTBOX_WAKEUPS_KEY, recovered)
    assert outbox.summary() == {"queued": 102}
    assert webhook_service._next_wakeup_attempt_at == 0.0


def test_transient_updates_are_durable_and_coalesce_only_unsent_state(outbox_database):
    red = Mock()
    pipe = red.pipeline.return_value

    first = enqueue_transient_message(
        _message(WebhookMessageType.SCOREBOARD),
        message_group_key="game",
        red=red,
    )

    latest = _message(WebhookMessageType.SCOREBOARD)
    latest.payload["content"] = "latest scoreboard state"
    second = enqueue_transient_message(latest, message_group_key="game", red=red)
    pipe.set.assert_not_called()
    pipe.sadd.assert_not_called()
    assert pipe.rpush.call_count == 2 and pipe.execute.call_count == 2
    assert first != second
    assert outbox.summary() == {"superseded": 1, "queued": 1}
    claim = outbox.claim("whs:1:transient_identifier:discord:scoreboard:123:game")
    assert claim and claim.id == second
    assert webhook_service.unpack_message(claim.payload).payload["content"] == "latest scoreboard state"


def test_webhook_queue_key_cache_reuses_discovery_within_refresh_interval():
    red = Mock()
    red.smembers.side_effect = [
        {b"__initialized__", b"whs:list:1", b"whs:transient_identifier:1"},
        {b"__initialized__", b"whs:list:2"},
    ]
    red.llen.return_value = 1
    red.exists.return_value = 1
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    expected = ["whs:list:1", "whs:transient_identifier:1"]
    assert cache.get_not_empty(now=10.0) == expected
    assert cache.get_not_empty(now=10.5) == expected
    red.scan_iter.assert_not_called()

    assert cache.get_not_empty(now=11.0) == ["whs:list:2"]
    assert red.smembers.call_count == 2


def test_webhook_queue_key_cache_filters_queues_deleted_between_scans():
    red = Mock()
    red.smembers.return_value = {
        b"__initialized__",
        b"whs:list:1",
        b"whs:transient_identifier:1",
    }
    red.llen.side_effect = [1, 0]
    red.exists.side_effect = [1, 0, 0]
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == [
        "whs:list:1",
        "whs:transient_identifier:1",
    ]
    assert cache.get_not_empty(now=10.5) == []
    red.scan_iter.assert_not_called()
    red.srem.assert_called_once()


def test_empty_durable_queue_does_not_construct_or_parse_a_message(monkeypatch):
    red = FakeStrictRedis()
    construct = Mock()
    monkeypatch.setattr(webhook_service, "construct_webhook", construct)

    asyncio.run(
        dequeue_message(
            red=red,
            client=Mock(),
            queue_id="whs:1:discord:audit:123",
            bucket_data=None,
            lock=asyncio.Lock(),
        )
    )

    construct.assert_not_called()
    assert outbox.summary() == {}


def test_legacy_empty_dequeue_metric_remains_available():
    red = FakeStrictRedis()
    webhook_service.record_empty_dequeue(red, "whs:1:discord:audit:123")
    assert int(red.get(EMPTY_DEQUEUE_COUNT)) == 1


def test_webhook_registry_imports_legacy_queues_once():
    red = Mock()
    red.smembers.side_effect = [set(), {b"__initialized__", b"whs:list:1"}]
    red.scan_iter.side_effect = [
        iter([b"whs:list:1"]),
        iter([b"whs:transient_identifier:1"]),
    ]
    red.llen.return_value = 1
    red.exists.return_value = 1
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == [
        "whs:list:1",
        "whs:transient_identifier:1",
    ]
    assert cache.get_not_empty(now=11.0) == ["whs:list:1"]
    assert red.scan_iter.call_count == 2
    red.sadd.assert_called_once()


def test_empty_webhook_registry_only_scans_during_initial_migration():
    red = Mock()
    red.smembers.side_effect = [set(), {b"__initialized__"}]
    red.scan_iter.side_effect = [iter([]), iter([])]
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == []
    assert cache.get_not_empty(now=11.0) == []
    assert red.scan_iter.call_count == 2
    red.sadd.assert_called_once()


def test_wakeup_lpop_and_legacy_discovery_never_consume_the_hint_namespace():
    red = FakeStrictRedis()
    first = enqueue_message(_message(), red=red)
    assert red.lpop(webhook_service.OUTBOX_WAKEUPS_KEY) == first.encode()
    second = enqueue_message(_message(), red=red)
    red.rpush(DEAD_LETTER_QUEUE, b"retained synthetic archive entry")
    registry = get_queue_registry_key()
    # An unfinished older discovery pass may have registered reserved keys.
    # Its scan/metadata cleanup must leave the hints/archive untouched.
    red.sadd(registry, webhook_service.OUTBOX_WAKEUPS_KEY,
             DEAD_LETTER_QUEUE, registry, "unrelated:queue")
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == []
    assert webhook_service.OUTBOX_WAKEUPS_KEY not in webhook_service.get_all_queue_keys(red=red)
    assert red.lrange(webhook_service.OUTBOX_WAKEUPS_KEY, 0, -1) == [second.encode()]
    assert red.lrange(DEAD_LETTER_QUEUE, 0, -1) == [b"retained synthetic archive entry"]
    assert red.smembers(registry) == {b"__initialized__"}
    assert outbox.summary() == {"queued": 2}
    assert outbox.list_review() == []


def test_partial_registry_discovers_unregistered_legacy_queues_before_initializing(monkeypatch):
    red = FakeStrictRedis()
    first, second = "whs:1:discord:audit:123", "whs:2:discord:audit:456"
    red.rpush(first, b"first synthetic report")
    red.rpush(second, b"second synthetic report")
    red.sadd(get_queue_registry_key(), first)
    scan = Mock(wraps=red.scan_iter)
    monkeypatch.setattr(red, "scan_iter", scan)
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == [first, second]
    assert cache.get_not_empty(now=11.0) == [first, second]
    assert red.smembers(get_queue_registry_key()) == {
        b"__initialized__", first.encode(), second.encode()}
    assert red.lrange(first, 0, -1) == [b"first synthetic report"]
    assert red.lrange(second, 0, -1) == [b"second synthetic report"]
    scan.assert_any_call(match="whs:*", _type="list")
    scan.assert_any_call(match="whs:*", _type="string")
    assert scan.call_count == 2
    assert outbox.summary() == {}


def test_dead_letter_list_is_redacted_for_operator_views():
    message = _message()
    entry = DeadLetterWebhookMessage(
        id="failed-delivery",
        message=message,
        source_queue_id="whs:1:discord:audit:123",
        reason="retry_limit_reached",
    )
    red = FakeStrictRedis()
    outbox.enqueue(entry.source_queue_id, message.model_dump_json().encode(),
                   message.server_number, public_id=entry.id, initial_status="review",
                   reason=entry.reason, created_at=entry.failed_at,
                   message_type=str(message.message_type), webhook_type=str(message.webhook_type))

    entries = get_dead_letter_messages(red=red)

    assert len(entries) == 1
    for key, expected in {
        "id": entry.id, "server_number": 1, "webhook_type": WebhookType.DISCORD,
        "message_type": WebhookMessageType.AUDIT, "retry_attempts": 0,
        "reason": "retry_limit_reached", "status": "review",
    }.items():
        assert entries[0][key] == expected
    assert entries[0]["failed_at"]
    assert "payload" not in entries[0]
    assert "token" not in str(entries[0])
    assert outbox.summary() == {"review": 1}
    assert red.llen(DEAD_LETTER_QUEUE) == 0


def test_review_archive_keeps_more_than_the_old_capacity_and_does_not_expire(outbox_database):
    red = FakeStrictRedis()
    for _ in range(501):
        status = move_to_dead_letter(message=_message(), queue_id="whs:1:discord:audit:123",
                                     reason="transport_error", red=red)
        assert status["reason"] == "transport_error"
    assert outbox.summary() == {"review": 501}
    assert len(get_dead_letter_messages(red=red, limit=1000)) == 501
    assert outbox.cleanup_sent(now=datetime.now(timezone.utc) + timedelta(days=60)) == 0
    assert all(row.payload for row in _stored_rows(outbox_database))
    assert red.exists(DEAD_LETTER_QUEUE) == 0


def test_dead_letter_retry_is_atomic_and_preserves_payload_on_storage_failure(monkeypatch, outbox_database):
    red = FakeStrictRedis()
    status = move_to_dead_letter(message=_message(), queue_id="whs:1:discord:audit:123",
                                 reason="transport_error", red=red)
    original = outbox.retry_review
    monkeypatch.setattr(outbox, "retry_review", Mock(side_effect=outbox.OutboxStorageError("synthetic outage")))
    with pytest.raises(outbox.OutboxStorageError):
        retry_dead_letter_message(status["id"], red=red)
    assert outbox.summary() == {"review": 1}
    assert _stored_rows(outbox_database)[0].payload
    monkeypatch.setattr(outbox, "retry_review", original)
    assert retry_dead_letter_message(status["id"], red=red) is True
    assert retry_dead_letter_message(status["id"], red=red) is False
    stored = _stored_rows(outbox_database)
    assert len(stored) == 1 and stored[0].message_id == status["id"] and stored[0].status == "queued"
    assert stored[0].payload
    assert red.lrange(webhook_service.OUTBOX_WAKEUPS_KEY, 0, -1) == [status["id"].encode()]


def test_old_accepted_message_is_retained_for_review_and_can_be_explicitly_retried(monkeypatch, outbox_database):
    from types import SimpleNamespace
    message = _message().model_copy(
        update={"sent_at": datetime.now(tz=timezone.utc) - timedelta(hours=2)}
    )
    red = FakeStrictRedis()
    enqueue_message(message, red=red)
    wh = SimpleNamespace(webhook_id="123", execute=AsyncMock(return_value=httpx.Response(204)))
    monkeypatch.setattr("rcon.webhook_service.construct_webhook", lambda **_: wh)

    asyncio.run(
        dequeue_message(
            red=red,
            client=Mock(),
            queue_id="whs:1:discord:audit:123",
            bucket_data=None,
            lock=asyncio.Lock(),
        )
    )

    wh.execute.assert_not_awaited()
    assert outbox.summary() == {"review": 1}
    stored = _stored_rows(outbox_database)
    assert stored[0].payload and stored[0].reason == "message_expired"
    assert retry_dead_letter_message(stored[0].message_id, red=red) is True
    asyncio.run(dequeue_message(red=red, client=Mock(), queue_id="whs:1:discord:audit:123",
                                bucket_data=None, lock=asyncio.Lock()))
    wh.execute.assert_awaited_once()
    assert outbox.summary() == {"sent": 1}
