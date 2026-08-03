from unittest.mock import Mock

from rcon.webhook_service import (
    WebhookType,
    handle_webhook_not_found,
)


def test_webhook_404_without_message_id_only_marks_webhook_error():
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
    red.hset.assert_called_once()
