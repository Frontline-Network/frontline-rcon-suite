import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon.campaign_delivery import (
    FAILED,
    QUEUED,
    SENT,
    enqueue_eligible_deliveries,
    finish_delivery,
    global_send_is_due,
    player_gap_is_due,
    recipient_is_eligible,
    send_test_message,
    session_is_eligible,
)
from rcon.user_config.auto_broadcast import AutoBroadcastMessage


def campaign(**overrides):
    values = {
        "id": "direct-campaign",
        "time_sec": 900,
        "message": "Hello {player_name} ({player_id})",
        "delivery_mode": "player_message",
        "min_session_minutes": 5,
    }
    values.update(overrides)
    return AutoBroadcastMessage(**values)


def test_session_threshold_is_inclusive():
    start = datetime(2026, 8, 19, 12, 0, 0)
    item = campaign(min_session_minutes=5)

    assert not session_is_eligible(
        item, start, start + timedelta(minutes=4, seconds=59)
    )
    assert session_is_eligible(item, start, start + timedelta(minutes=5))


def test_recipient_groups_use_current_vip_state():
    assert recipient_is_eligible(campaign(recipient_group="all"), False)
    assert recipient_is_eligible(campaign(recipient_group="all"), True)
    assert recipient_is_eligible(campaign(recipient_group="vip"), True)
    assert not recipient_is_eligible(campaign(recipient_group="vip"), False)
    assert recipient_is_eligible(campaign(recipient_group="non_vip"), False)
    assert not recipient_is_eligible(campaign(recipient_group="non_vip"), True)


def test_global_and_per_player_intervals_are_inclusive():
    now = datetime(2026, 8, 19, 12, 10, 0)
    assert global_send_is_due(None, 10, now)
    assert not global_send_is_due(now - timedelta(seconds=9), 10, now)
    assert global_send_is_due(now - timedelta(seconds=10), 10, now)
    assert player_gap_is_due(None, 300, now)
    assert not player_gap_is_due(now - timedelta(seconds=299), 300, now)
    assert player_gap_is_due(now - timedelta(seconds=300), 300, now)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def __iter__(self):
        return iter(self.rows)


class FakeEnqueueSession:
    def __init__(self):
        self.rows = []

    def query(self, model):
        return FakeQuery(self.rows)

    def add(self, row):
        self.rows.append(row)


def test_enqueue_is_idempotent_for_campaign_and_session(monkeypatch):
    fake_session = FakeEnqueueSession()

    @contextmanager
    def fake_enter_session():
        yield fake_session

    monkeypatch.setattr("rcon.campaign_delivery.enter_session", fake_enter_session)
    now = datetime(2026, 8, 19, 12, 10, 0)
    kwargs = {
        "campaigns": [campaign()],
        "online_players": {
            "player-1": {
                "player_id": "player-1",
                "player_name": "Alice",
                "is_vip": False,
            }
        },
        "active_sessions": {
            "player-1": {
                "player_db_id": 7,
                "session_id": 11,
                "start": now - timedelta(minutes=10),
            }
        },
        "server_number": 1,
        "player_count": 1,
        "seeding_config": None,
        "now": now,
    }

    assert enqueue_eligible_deliveries(**kwargs) == 1
    assert enqueue_eligible_deliveries(**kwargs) == 0
    assert len(fake_session.rows) == 1


def test_finish_delivery_retries_then_fails(monkeypatch):
    delivery = SimpleNamespace(
        id=1,
        status="sending",
        attempt_count=1,
        updated_at=None,
        sent_at=None,
        next_attempt_at=None,
        last_error=None,
    )

    class FakeSession:
        def get(self, model, delivery_id, **kwargs):
            return delivery

    @contextmanager
    def fake_enter_session():
        yield FakeSession()

    monkeypatch.setattr("rcon.campaign_delivery.enter_session", fake_enter_session)
    now = datetime(2026, 8, 19, 12, 0, 0)

    finish_delivery(1, success=False, now=now, error="temporary")
    assert delivery.status == QUEUED
    assert delivery.next_attempt_at == now + timedelta(seconds=30)

    delivery.status = "sending"
    finish_delivery(1, success=False, now=now, error="response lost", uncertain=True)
    assert delivery.status == FAILED
    assert delivery.next_attempt_at is None

    delivery.attempt_count = 3
    delivery.status = "sending"
    finish_delivery(1, success=False, now=now, error="terminal")
    assert delivery.status == FAILED
    assert delivery.next_attempt_at is None

    delivery.status = "sending"
    finish_delivery(1, success=True, now=now)
    assert delivery.status == SENT
    assert delivery.sent_at == now


def test_direct_test_formats_player_context_without_consuming_delivery():
    ctl = Mock()
    ctl.get_player_ids.return_value = [("Alice", "player-1")]
    ctl.message_player.return_value = True
    formatted = send_test_message(ctl, campaign(), "player-1")

    assert formatted == "Hello Alice (player-1)"
    ctl.message_player.assert_called_once_with(
        "player-1",
        "Hello Alice (player-1)",
        save_message=False,
        player_name="Alice",
    )
