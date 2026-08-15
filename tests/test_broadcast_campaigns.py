import os

from pydantic import ValidationError

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon.broadcast import (
    campaign_is_eligible,
    manual_broadcast_is_active,
    seeding_is_active,
)
from rcon.user_config.auto_broadcast import (
    AutoBroadcastMessage,
    AutoBroadcastUserConfig,
)
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig


def test_legacy_broadcast_message_keeps_existing_defaults():
    campaign = AutoBroadcastMessage(time_sec=120, message="Join our community")

    assert campaign.enabled is True
    assert campaign.min_players == 0
    assert campaign.max_players == 100
    assert campaign.pause_during_seeding is False


def test_campaign_rejects_inverted_player_range():
    try:
        AutoBroadcastMessage(
            time_sec=120,
            message="Join our community",
            min_players=50,
            max_players=20,
        )
    except ValidationError:
        return

    raise AssertionError("An inverted campaign player range must be rejected")


def test_campaign_player_range_is_inclusive():
    campaign = AutoBroadcastMessage(
        time_sec=120,
        message="Join our community",
        min_players=20,
        max_players=40,
    )

    assert campaign_is_eligible(campaign, 20)
    assert campaign_is_eligible(campaign, 40)
    assert not campaign_is_eligible(campaign, 19)
    assert not campaign_is_eligible(campaign, 41)


def test_disabled_campaign_is_never_eligible():
    campaign = AutoBroadcastMessage(
        enabled=False,
        time_sec=120,
        message="Join our community",
    )

    assert not campaign_is_eligible(campaign, 50)


def test_campaign_can_pause_while_seeding_rules_apply():
    seeding = AutoModSeedingUserConfig(
        enabled=True,
        dont_do_anything_below_this_number_of_players=1,
        enforce_cap_fight={"min_players": 1, "max_players": 40},
    )
    campaign = AutoBroadcastMessage(
        time_sec=120,
        message="VIP access is available",
        pause_during_seeding=True,
    )

    assert seeding_is_active(seeding, 30)
    assert not campaign_is_eligible(campaign, 30, seeding)
    assert campaign_is_eligible(campaign, 41, seeding)


def test_manual_broadcast_defers_campaign_cycle(monkeypatch):
    campaign = AutoBroadcastMessage(time_sec=120, message="VIP access")

    class FakeRcon:
        def get_broadcast_message(self):
            return "Important admin notice"

    monkeypatch.setattr("rcon.broadcast.format_message", lambda _, message: message)

    assert manual_broadcast_is_active(FakeRcon(), [campaign])


def test_current_campaign_message_does_not_defer_cycle(monkeypatch):
    campaign = AutoBroadcastMessage(time_sec=120, message="VIP access")

    class FakeRcon:
        def get_broadcast_message(self):
            return "VIP access"

    monkeypatch.setattr("rcon.broadcast.format_message", lambda _, message: message)

    assert not manual_broadcast_is_active(FakeRcon(), [campaign])


def test_structured_campaign_fields_are_persisted(monkeypatch):
    persisted = {}
    monkeypatch.setattr(
        "rcon.user_config.auto_broadcast.set_user_config",
        lambda key, value: persisted.update({"key": key, "value": value}),
    )

    AutoBroadcastUserConfig.save_to_db(
        {
            "enabled": True,
            "randomize": False,
            "messages": [
                {
                    "id": "vip-access",
                    "title": "VIP access",
                    "enabled": True,
                    "time_sec": 900,
                    "message": "Get VIP access",
                    "min_players": 30,
                    "max_players": 100,
                    "pause_during_seeding": True,
                }
            ],
        }
    )

    campaign = persisted["value"].messages[0]
    assert campaign.id == "vip-access"
    assert campaign.min_players == 30
    assert campaign.pause_during_seeding is True


def test_legacy_string_config_remains_supported(monkeypatch):
    persisted = {}
    monkeypatch.setattr(
        "rcon.user_config.auto_broadcast.set_user_config",
        lambda key, value: persisted.update({"value": value}),
    )

    AutoBroadcastUserConfig.save_to_db(
        {
            "enabled": True,
            "randomize": False,
            "messages": ["120 Legacy broadcast"],
        }
    )

    campaign = persisted["value"].messages[0]
    assert campaign.time_sec == 120
    assert campaign.message == "Legacy broadcast"
    assert campaign.enabled is True
