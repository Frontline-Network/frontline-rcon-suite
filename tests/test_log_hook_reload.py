from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import Mock

from rcon.logs import loop


def test_reload_removes_deleted_webhooks_and_keeps_builtin_hooks(monkeypatch):
    builtin = lambda *_: None
    hooks = defaultdict(list, {"KILL": [builtin]})
    monkeypatch.setattr(loop, "HOOKS", hooks)
    webhook = SimpleNamespace(url="https://example.invalid/fake-token")
    config = SimpleNamespace(webhooks=[SimpleNamespace(webhook=webhook, log_types=[SimpleNamespace(value="KILL")])])
    monkeypatch.setattr(loop.LogLineWebhookUserConfig, "load_from_db", lambda: config)
    loop.load_generic_hooks.__wrapped__()
    assert len(hooks["KILL"]) == 2
    config.webhooks = []
    loop.load_generic_hooks.__wrapped__()
    assert hooks["KILL"] == [builtin]


def test_failed_webhook_does_not_log_exception_with_token(monkeypatch, caplog):
    from rcon.leadership_vote import domain
    monkeypatch.setattr(domain, "suppress_public_chat", lambda _: False)
    monkeypatch.setattr(loop.RconServerSettingsUserConfig, "load_from_db", lambda: SimpleNamespace(short_name="test"))
    webhook = SimpleNamespace(url="https://example.invalid/fake-token", user_mentions=[], role_mentions=[])
    discord_hook = Mock()
    discord_hook.execute.side_effect = RuntimeError("failed at https://example.invalid/fake-token")
    monkeypatch.setattr(loop, "make_hook", lambda _: discord_hook)
    loop.send_log_line_webhook_message(webhook, None, {"line_without_time": "test", "timestamp_ms": 0})
    assert "Discord log webhook delivery failed" in caplog.text
    assert "fake-token" not in caplog.text
