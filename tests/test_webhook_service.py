import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import orjson

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
from rcon import webhook_service


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


def test_webhook_404_without_message_id_marks_error_and_purges_webhook_queue():
    red = Mock()

    handle_webhook_not_found(
        red=red,
        queue_id="whs:1:discord:audit:123",
        payload={"webhook_id": "123"},
        webhook_type=WebhookType.DISCORD,
        webhook_id="123",
    )

    red.set.assert_not_called()
    red.lrange.assert_not_called()
    red.delete.assert_called_once_with("whs:1:discord:audit:123")
    red.srem.assert_called_once_with(
        get_queue_registry_key(), "whs:1:discord:audit:123"
    )
    red.hset.assert_called_once()


def test_webhook_404_with_message_id_marks_edit_and_clears_related_queue_items():
    red = Mock()
    red.lrange.return_value = []

    handle_webhook_not_found(
        red=red,
        queue_id="whs:1:discord:scoreboard:123",
        payload={"webhook_id": "123", "message_id": "456"},
        webhook_type=WebhookType.DISCORD,
        webhook_id="123",
    )

    red.set.assert_called_once()
    red.lrange.assert_called_once_with("whs:1:discord:scoreboard:123", 0, -1)
    red.delete.assert_not_called()
    red.srem.assert_not_called()
    red.hset.assert_called_once()


def test_enqueue_registers_persistent_queue():
    red = Mock()

    enqueue_message(_message(), red=red)

    red.rpush.assert_called_once()
    red.sadd.assert_called_once_with(
        get_queue_registry_key(),
        "__initialized__",
        "whs:1:discord:audit:123",
    )


def test_enqueue_registers_transient_queue():
    red = Mock()

    enqueue_transient_message(
        _message(WebhookMessageType.SCOREBOARD),
        message_group_key="game",
        red=red,
    )

    red.set.assert_called_once()
    red.sadd.assert_called_once_with(
        get_queue_registry_key(),
        "__initialized__",
        "whs:1:transient_identifier:discord:scoreboard:123:game",
    )


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


def test_dequeue_lpop_race_is_counted_without_json_error():
    red = Mock()
    red.lpop.return_value = None

    asyncio.run(
        dequeue_message(
            red=red,
            client=Mock(),
            queue_id="whs:1:discord:audit:123",
            bucket_data=None,
            lock=asyncio.Lock(),
        )
    )

    red.incr.assert_called_once_with(EMPTY_DEQUEUE_COUNT)


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


def test_dead_letter_list_is_redacted_for_operator_views():
    message = _message()
    entry = DeadLetterWebhookMessage(
        id="failed-delivery",
        message=message,
        source_queue_id="whs:1:discord:audit:123",
        reason="retry_limit_reached",
    )
    red = Mock()
    red.lrange.return_value = [entry.model_dump_json()]

    entries = get_dead_letter_messages(red=red)

    assert entries == [
        {
            "id": "failed-delivery",
            "server_number": 1,
            "webhook_type": WebhookType.DISCORD,
            "message_type": WebhookMessageType.AUDIT,
            "retry_attempts": 0,
            "reason": "retry_limit_reached",
            "failed_at": entry.failed_at,
        }
    ]
    assert "payload" not in entries[0]
    assert "token" not in str(entries[0])


def test_dead_letter_is_bounded_and_expires():
    red = Mock()

    status = move_to_dead_letter(
        message=_message(),
        queue_id="whs:1:discord:audit:123",
        reason="transport_error",
        red=red,
    )

    assert status["reason"] == "transport_error"
    assert red.lpush.call_args.args[0] == DEAD_LETTER_QUEUE
    red.ltrim.assert_called_once()
    red.expire.assert_called_once()


def test_dead_letter_retry_removes_entry_before_requeueing():
    entry = DeadLetterWebhookMessage(
        id="retry-me",
        message=_message(),
        source_queue_id="whs:1:discord:audit:123",
        reason="transport_error",
    )
    red = Mock()
    raw_entry = entry.model_dump_json()
    red.lrange.return_value = [raw_entry]
    red.lrem.return_value = 1

    assert retry_dead_letter_message("retry-me", red=red) is True
    red.lrem.assert_called_once_with(DEAD_LETTER_QUEUE, 1, raw_entry)
    assert red.rpush.call_args.args[0] == "whs:1:discord:audit:123"
    assert red.sadd.call_args.args[0] == get_queue_registry_key()


def test_expired_message_moves_to_dead_letter_without_contacting_discord(monkeypatch):
    message = _message().model_copy(
        update={"sent_at": datetime.now(tz=timezone.utc) - timedelta(hours=2)}
    )
    red = Mock()
    # Persistent webhook queues keep the Pydantic JSON string as a Redis JSON
    # value, matching ``enqueue_message``.
    red.lpop.return_value = orjson.dumps(message.model_dump_json())
    construct = Mock()
    monkeypatch.setattr("rcon.webhook_service.construct_webhook", construct)

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
    assert red.lpush.call_args.args[0] == DEAD_LETTER_QUEUE
