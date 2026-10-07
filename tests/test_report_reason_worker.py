"""Fake HTTP and SQLite: full worker handoff, no live credentials or model."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.test_report_admin_api import setup, db  # initializes isolated Django
from tests.test_report_reason import (
    semantic,
    decision,
    report,
    service,
    current,
    transport,
)
from api import report_reason_worker as worker


@pytest.fixture
def connection(monkeypatch):
    integration = SimpleNamespace(
        service_url="https://discord.example",
        installation_id="test-installation",
        outbound_capability_ciphertext="outbound",
        ai_api_key_ciphertext="encrypted-key",
        ai_config={"provider": "api_key", "ai_model": "configured-model"},
    )
    monkeypatch.setattr(
        worker.DiscordReportIntegration.objects,
        "filter",
        lambda **kw: SimpleNamespace(first=lambda: integration),
    )
    monkeypatch.setattr(
        worker,
        "decrypt_capability",
        lambda value: "mock-secret-value-long-enough-" + value,
    )
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "decision": decision(),
        "model": "configured-model",
        "prompt_version": "report-reason-1",
    }
    http = Mock()
    http.post.return_value = response
    return integration, http


def test_worker_uses_complete_message_and_never_sends_player_ids(semantic, connection):
    _, http = connection
    raw = "!admin BattlefieldHero never answers us in command chat (he rejoined)"
    i = report(semantic, raw)
    assert worker.process_one(http)
    http.post.assert_called_once()
    payload = http.post.call_args.kwargs["json"]
    assert payload["message"] == raw
    assert all(set(p) == {"name", "team", "role", "squad"} for p in payload["roster"])
    assert not worker.process_one(http)
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert "mock-secret" not in str(current(semantic[0], i["id"]))


@pytest.mark.parametrize(
    "failure",
    [
        "provider",
        "missing_key",
        "timeout",
        "malformed",
        "undelivered",
        "late",
        "takeover",
        "concurrent",
    ],
)
def test_worker_failure_and_races(semantic, connection, monkeypatch, failure):
    integration, http = connection
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    if failure == "provider":
        integration.ai_config["provider"] = "managed"
    if failure == "missing_key":
        integration.ai_api_key_ciphertext = None
    if failure == "timeout":
        http.post.side_effect = TimeoutError("must-not-leak-secret")
    if failure == "malformed":
        http.post.return_value.json.return_value = {"decision": {"action": "kick"}}
    if failure == "undelivered":
        monkeypatch.setattr(service, "delivered", lambda *a: False)
    if failure in {"late", "takeover", "concurrent"}:
        response = http.post.return_value

        def during_call(*args, **kwargs):
            if failure == "late":
                semantic[0].clock.now += 61
            elif failure == "takeover":
                with semantic[0]() as sess:
                    service.cancel_player(sess, 1, "target")
            else:
                assert not worker.process_one(http)
            return response

        http.post.side_effect = during_call
    worker.process_one(http)
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    if failure == "concurrent":
        api.kick.assert_called_once()
        http.post.assert_called_once()
    else:
        api.kick.assert_not_called()
    if failure in {"provider", "missing_key", "undelivered"}:
        http.post.assert_not_called()
    if failure != "undelivered":
        assert not worker.process_one(http)


def test_codex_uses_only_configured_installation_account(semantic, connection):
    integration, http = connection
    integration.ai_config["provider"] = "codex"
    integration.ai_api_key_ciphertext = None
    report(semantic, "!admin BattlefieldHero never answers us in command chat")
    worker.process_one(http)
    assert http.post.call_args.kwargs["json"]["api_key"] is None
    assert http.post.call_args.kwargs["json"]["ai_provider"] == "codex"


def test_confirmed_not_started_busy_waits_then_analyzes_once(semantic, connection):
    _, http = connection
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    response = http.post.return_value
    response.status_code = 429
    response.json.return_value = {"detail": "report_reason_not_started_busy"}
    assert worker.process_one(http)
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "classifying"
    assert not worker.process_one(http)  # backoff, no tight retry loop
    assert http.post.call_count == 1
    semantic[0].clock.now += 3
    semantic[2]["captured_at"] = semantic[0].clock.now
    response.status_code = 200
    response.json.return_value = {
        "decision": decision(),
        "model": "configured-model",
        "prompt_version": "test",
    }
    assert worker.process_one(http)
    assert not worker.process_one(http)
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert http.post.call_count == 2  # admission refusal, then actual inference


@pytest.mark.parametrize("change", ["expired", "takeover", "generic429", "generic503"])
def test_busy_admission_is_bounded_and_not_generic_retry(semantic, connection, change):
    _, http = connection
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    response = http.post.return_value
    response.status_code = 429 if change != "generic503" else 503
    response.json.return_value = {
        "detail": (
            "other"
            if change.startswith("generic")
            else "report_reason_not_started_busy"
        )
    }
    if change.startswith("generic"):
        response.raise_for_status.side_effect = RuntimeError("HTTP failure")
    assert worker.process_one(http)
    if change == "expired":
        semantic[0].clock.now += 61
    elif change == "takeover":
        with semantic[0]() as sess:
            service.cancel_player(sess, 1, "target")
    semantic[0].clock.now += 3
    semantic[2]["captured_at"] = semantic[0].clock.now
    worker.process_one(http)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    http.post.assert_called_once()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "manual"
