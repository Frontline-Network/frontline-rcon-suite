from unittest.mock import Mock

import pydantic
import pytest

from rcon.discord import probe_chat_webhook, test_chat_webhook
from rcon.user_config.webhooks import ChatDiscordWebhook


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


def valid_discord_response():
    response = Mock(status_code=200)
    response.json.return_value = {"id": "123", "token": "secret"}
    return response


def test_chat_webhook_url_requires_canonical_discord_endpoint():
    with pytest.raises(pydantic.ValidationError):
        ChatDiscordWebhook(url="https://example.com/api/webhooks/123/token")

    with pytest.raises(pydantic.ValidationError):
        ChatDiscordWebhook(url="http://discord.com/api/webhooks/123/token")

    hook = ChatDiscordWebhook(url="https://discord.com/api/webhooks/123/token")
    assert str(hook.url) == "https://discord.com/api/webhooks/123/token"


def test_probe_records_a_safe_invalid_diagnostic(monkeypatch):
    response = Mock(status_code=404)
    redis = FakeRedis()
    monkeypatch.setattr("rcon.discord.requests.get", Mock(return_value=response))
    monkeypatch.setattr("rcon.discord.get_redis_client", lambda: redis)

    result = probe_chat_webhook("https://discord.com/api/webhooks/123/token")

    assert result["status"] == "invalid"
    assert "token" not in result["last_error"].lower()
    assert len(redis.values) == 1
    assert "token" not in next(iter(redis.values))


def test_test_message_disables_all_mentions(monkeypatch):
    redis = FakeRedis()
    post = Mock(return_value=Mock(status_code=204))
    monkeypatch.setattr(
        "rcon.discord.requests.get", Mock(return_value=valid_discord_response())
    )
    monkeypatch.setattr("rcon.discord.requests.post", post)
    monkeypatch.setattr("rcon.discord.get_redis_client", lambda: redis)

    result = test_chat_webhook("https://discord.com/api/webhooks/123/token")

    assert result["status"] == "valid"
    assert result["test_message_delivered"] is True
    assert post.call_args.kwargs["json"]["allowed_mentions"] == {"parse": []}
