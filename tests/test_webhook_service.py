from unittest.mock import Mock

from rcon.webhook_service import (
    WebhookQueueKeyCache,
    WebhookMessage,
    WebhookMessageType,
    WebhookType,
    enqueue_message,
    enqueue_transient_message,
    get_queue_registry_key,
    handle_webhook_not_found,
)


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
    red.exists.side_effect = [1, 0]
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == [
        "whs:list:1",
        "whs:transient_identifier:1",
    ]
    assert cache.get_not_empty(now=10.5) == []
    red.scan_iter.assert_not_called()
    red.srem.assert_called_once()


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
