import hashlib
import hmac
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import requests

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon.user_config.auto_broadcast import AutoBroadcastUserConfig, VipLifecycleConfig
from rcon.vip_lifecycle import (
    RULE_TRIAL_ACTIVE,
    RULE_TRIAL_EXPIRED,
    RULE_TRIAL_EXPIRING,
    RULE_UNVERIFIED,
    LifecycleDecision,
    _prepare_delivery,
    classify_status,
    clear_status_cache,
    delivery_status,
    feature_enabled,
    fetch_statuses,
    process_once,
    unverified_cooldown_elapsed,
)

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)


def status(**overrides):
    result = {
        "player_id": "player-1",
        "server_family": "hll_vietnam",
        "status_known": True,
        "verified": True,
        "vip_active": True,
        "grant_source": "trial",
        "expires_at": (NOW + timedelta(days=5)).isoformat(),
        "has_purchased_vip": False,
        "status_version": "v1",
    }
    result.update(overrides)
    return result


def test_legacy_campaign_config_keeps_lifecycle_disabled():
    config = AutoBroadcastUserConfig(
        enabled=True,
        randomize=False,
        messages=[],
    )

    assert config.vip_lifecycle.enabled is False
    assert config.vip_lifecycle.server_family == "hll_vietnam"
    assert config.vip_lifecycle.expiry_window_hours == 48


def test_private_feature_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", raising=False)

    assert feature_enabled() is False
    result = delivery_status()
    assert result["available"] is False
    assert result["deliveries"] == []
    assert result["generated_at"].tzinfo is not None


def test_private_feature_accepts_explicit_true_value(monkeypatch):
    monkeypatch.setenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "true")

    assert feature_enabled() is True


def test_all_four_lifecycle_states_are_classified():
    unverified = classify_status(
        status(
            verified=False,
            vip_active=False,
            grant_source="none",
            expires_at=None,
        ),
        now=NOW,
        expiry_window_hours=48,
    )
    active = classify_status(status(), now=NOW, expiry_window_hours=48)
    expiring = classify_status(
        status(expires_at=(NOW + timedelta(hours=48)).isoformat()),
        now=NOW,
        expiry_window_hours=48,
    )
    expired = classify_status(
        status(vip_active=False, expires_at=NOW.isoformat()),
        now=NOW,
        expiry_window_hours=48,
    )

    assert unverified and unverified.rule == RULE_UNVERIFIED
    assert active and active.rule == RULE_TRIAL_ACTIVE
    assert expiring and expiring.rule == RULE_TRIAL_EXPIRING
    assert expired and expired.rule == RULE_TRIAL_EXPIRED


def test_status_fingerprint_does_not_depend_on_session_or_check_time():
    first = classify_status(status(), now=NOW, expiry_window_hours=48)
    second = classify_status(
        status(), now=NOW + timedelta(minutes=30), expiry_window_hours=48
    )

    assert first and second
    assert first.status_fingerprint == second.status_fingerprint


def test_expiry_window_boundary_is_exact():
    at_boundary = classify_status(
        status(expires_at=(NOW + timedelta(hours=48)).isoformat()),
        now=NOW,
        expiry_window_hours=48,
    )
    outside_boundary = classify_status(
        status(expires_at=(NOW + timedelta(hours=48, microseconds=1)).isoformat()),
        now=NOW,
        expiry_window_hours=48,
    )

    assert at_boundary and at_boundary.rule == RULE_TRIAL_EXPIRING
    assert outside_boundary and outside_boundary.rule == RULE_TRIAL_ACTIVE


def test_unverified_cooldown_is_inclusive():
    assert not unverified_cooldown_elapsed(
        NOW - timedelta(days=7, microseconds=-1),
        cooldown_days=7,
        now=NOW,
    )
    assert unverified_cooldown_elapsed(
        NOW - timedelta(days=7), cooldown_days=7, now=NOW
    )


def test_paid_or_ambiguous_players_never_receive_advertising():
    assert (
        classify_status(
            status(has_purchased_vip=True, grant_source="paid"),
            now=NOW,
            expiry_window_hours=48,
        )
        is None
    )
    assert (
        classify_status(status(status_known=False), now=NOW, expiry_window_hours=48)
        is None
    )
    assert (
        classify_status(status(expires_at=None), now=NOW, expiry_window_hours=48)
        is None
    )


def test_status_client_batches_and_caches(monkeypatch):
    clear_status_cache()
    monkeypatch.setenv(
        "FRONTLINE_VIP_STATUS_URL",
        "https://fln.gg/wp-json/frontline-vip/v1/lifecycle-status",
    )
    monkeypatch.setenv("FRONTLINE_VIP_REDEEM_SECRET", "s" * 32)
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "success": True,
        "server_family": "hll_vietnam",
        "players": [
            status(player_id="player-1"),
            status(player_id="player-2", status_version="v2"),
        ],
    }
    post = Mock(return_value=response)

    first = fetch_statuses(
        {"player-1", "player-2"},
        server_family="hll_vietnam",
        cache_seconds=60,
        post=post,
    )
    second = fetch_statuses(
        {"player-1", "player-2"},
        server_family="hll_vietnam",
        cache_seconds=60,
        post=post,
    )

    assert set(first) == {"player-1", "player-2"}
    assert second == first
    post.assert_called_once()
    sent = json.loads(post.call_args.kwargs["data"])
    assert sent == {
        "player_ids": ["player-1", "player-2"],
        "server_family": "hll_vietnam",
    }
    headers = post.call_args.kwargs["headers"]
    assert headers["X-FLN-Timestamp"].isdigit()
    assert re.fullmatch(r"[a-f0-9]{32}", headers["X-FLN-Nonce"])
    signed = (
        headers["X-FLN-Timestamp"].encode()
        + b"\n"
        + headers["X-FLN-Nonce"].encode()
        + b"\n"
        + post.call_args.kwargs["data"]
    )
    assert headers["X-FLN-Signature"] == hmac.new(
        ("s" * 32).encode(), signed, hashlib.sha256
    ).hexdigest()


def test_status_client_rejects_rows_from_another_server_family(monkeypatch):
    clear_status_cache()
    monkeypatch.setenv("FRONTLINE_VIP_STATUS_URL", "https://fln.gg/status")
    monkeypatch.setenv("FRONTLINE_VIP_REDEEM_SECRET", "s" * 32)
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "success": True,
        "server_family": "hll_vietnam",
        "players": [status(server_family="hll")],
    }

    assert (
        fetch_statuses(
            {"player-1"},
            server_family="hll_vietnam",
            cache_seconds=60,
            post=Mock(return_value=response),
        )
        == {}
    )


def test_status_client_rejects_inconsistent_status_rows(monkeypatch):
    clear_status_cache()
    monkeypatch.setenv("FRONTLINE_VIP_STATUS_URL", "https://fln.gg/status")
    monkeypatch.setenv("FRONTLINE_VIP_REDEEM_SECRET", "s" * 32)
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "success": True,
        "server_family": "hll_vietnam",
        "players": [
            status(
                verified=False,
                vip_active=True,
                grant_source="trial",
                has_purchased_vip=False,
            )
        ],
    }

    assert (
        fetch_statuses(
            {"player-1"},
            server_family="hll_vietnam",
            cache_seconds=60,
            post=Mock(return_value=response),
        )
        == {}
    )


def test_status_api_failure_is_fail_closed(monkeypatch):
    clear_status_cache()
    monkeypatch.setenv(
        "FRONTLINE_VIP_STATUS_URL",
        "https://fln.gg/wp-json/frontline-vip/v1/lifecycle-status",
    )
    monkeypatch.setenv("FRONTLINE_VIP_REDEEM_SECRET", "s" * 32)
    post = Mock(side_effect=requests.ConnectionError("offline"))

    assert (
        fetch_statuses(
            {"player-1"},
            server_family="hll_vietnam",
            cache_seconds=60,
            post=post,
        )
        == {}
    )


def test_process_test_mode_never_sends_a_real_message(monkeypatch):
    monkeypatch.setenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "true")
    config = VipLifecycleConfig(enabled=True, test_mode=True)
    ctl = Mock()
    finished = Mock()
    monkeypatch.setattr(
        "rcon.vip_lifecycle._local_server_family", lambda: "hll_vietnam"
    )
    monkeypatch.setattr(
        "rcon.vip_lifecycle._online_players", lambda _ctl: {"player-1": "Alice"}
    )
    monkeypatch.setattr("rcon.vip_lifecycle._blocked_player_ids", lambda *_: set())
    monkeypatch.setattr(
        "rcon.vip_lifecycle.fetch_statuses",
        lambda *_args, **_kwargs: {"player-1": status()},
    )
    monkeypatch.setattr("rcon.vip_lifecycle._prepare_delivery", lambda **_: 17)
    monkeypatch.setattr("rcon.vip_lifecycle._finish_delivery", finished)

    result = process_once(ctl, config, now=NOW)

    assert result["simulated"] == 1
    ctl.message_player.assert_not_called()
    finished.assert_called_once_with(17, status="simulated", now=NOW)


def test_process_skips_delivery_when_status_api_is_unavailable(monkeypatch):
    monkeypatch.setenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "true")
    config = VipLifecycleConfig(enabled=True)
    ctl = Mock()
    prepare = Mock()
    monkeypatch.setattr(
        "rcon.vip_lifecycle._local_server_family", lambda: "hll_vietnam"
    )
    monkeypatch.setattr(
        "rcon.vip_lifecycle._online_players", lambda _ctl: {"player-1": "Alice"}
    )
    monkeypatch.setattr("rcon.vip_lifecycle._blocked_player_ids", lambda *_: set())
    monkeypatch.setattr(
        "rcon.vip_lifecycle.fetch_statuses", lambda *_args, **_kwargs: {}
    )
    monkeypatch.setattr("rcon.vip_lifecycle._prepare_delivery", prepare)

    process_once(ctl, config, now=NOW)

    prepare.assert_not_called()
    ctl.message_player.assert_not_called()


def test_process_is_inert_when_private_feature_is_not_enabled(monkeypatch):
    monkeypatch.delenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", raising=False)
    config = VipLifecycleConfig(enabled=True)
    ctl = Mock()
    online_players = Mock()
    monkeypatch.setattr("rcon.vip_lifecycle._online_players", online_players)

    result = process_once(ctl, config, now=NOW)

    assert result == {"online": 0, "eligible": 0, "sent": 0, "simulated": 0}
    online_players.assert_not_called()


def test_existing_persistent_claim_is_never_retried(monkeypatch):
    player = SimpleNamespace(id=7)
    existing_delivery = SimpleNamespace(status="failed", attempt_count=1)

    class FakeQuery:
        def __init__(self, value):
            self.value = value

        def filter(self, *_args):
            return self

        def one_or_none(self):
            return self.value

    class FakeSession:
        def query(self, model):
            from rcon.models import PlayerID, VipLifecycleDelivery

            if model is PlayerID:
                return FakeQuery(player)
            if model is VipLifecycleDelivery:
                return FakeQuery(existing_delivery)
            raise AssertionError(f"Unexpected model: {model}")

        def add(self, _value):
            raise AssertionError("An existing lifecycle claim must not be recreated")

    @contextmanager
    def fake_enter_session():
        yield FakeSession()

    monkeypatch.setattr("rcon.vip_lifecycle.enter_session", fake_enter_session)

    assert (
        _prepare_delivery(
            player_id="player-1",
            player_name="Alice",
            decision=LifecycleDecision(RULE_TRIAL_ACTIVE, "f" * 64),
            message="Personal message",
            config=VipLifecycleConfig(enabled=True),
            server_number=1,
            now=NOW,
        )
        is None
    )
    _prepare_delivery,
