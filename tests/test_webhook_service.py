from unittest.mock import Mock, call

from rcon.webhook_service import (
    WebhookQueueKeyCache,
    WebhookType,
    handle_webhook_not_found,
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
    red.hset.assert_called_once()


def test_webhook_queue_key_cache_reuses_discovery_within_refresh_interval():
    red = Mock()
    red.scan_iter.side_effect = [
        iter([b"whs:list:1"]),
        iter([b"whs:transient_identifier:1"]),
        iter([b"whs:list:2"]),
        iter([]),
    ]
    red.llen.return_value = 1
    red.exists.return_value = 1
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    expected = ["whs:list:1", "whs:transient_identifier:1"]
    assert cache.get_not_empty(now=10.0) == expected
    assert cache.get_not_empty(now=10.5) == expected
    assert red.scan_iter.call_args_list == [
        call(match="whs*", _type="list"),
        call(match="whs*", _type="string"),
    ]

    assert cache.get_not_empty(now=11.0) == ["whs:list:2"]
    assert red.scan_iter.call_count == 4


def test_webhook_queue_key_cache_filters_queues_deleted_between_scans():
    red = Mock()
    red.scan_iter.side_effect = [
        iter([b"whs:list:1"]),
        iter([b"whs:transient_identifier:1"]),
    ]
    red.llen.side_effect = [1, 0]
    red.exists.side_effect = [1, 0]
    cache = WebhookQueueKeyCache(red=red, refresh_interval_secs=1.0)

    assert cache.get_not_empty(now=10.0) == [
        "whs:list:1",
        "whs:transient_identifier:1",
    ]
    assert cache.get_not_empty(now=10.5) == []
    assert red.scan_iter.call_count == 2
