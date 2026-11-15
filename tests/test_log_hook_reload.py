from collections import defaultdict
from types import SimpleNamespace

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
