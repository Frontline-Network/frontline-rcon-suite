from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import humanize
import pytest

from rcon.seed_vip import utils
from rcon.user_config.seed_vip import SeedVIPUserConfig

NOW = datetime(2026, 10, 16, 18, 0, tzinfo=timezone.utc)
GERMAN_MESSAGE = (
    "SEEDING BEENDET! Danke, dass du uns beim Seeden geholfen hast. "
    "Es gelten jetzt die normalen Spielregeln.\n\n"
    "Deine VIP-Belohnung: {vip_reward}.\n"
    "Dein VIP läuft {vip_expiration} ab."
)


@pytest.fixture(autouse=True)
def fixed_clock_and_locale(monkeypatch):
    clock = Mock(wraps=datetime)
    clock.now.side_effect = lambda tz=None: (
        NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)
    )
    monkeypatch.setattr(utils, "datetime", clock)
    humanize.deactivate()
    yield
    humanize.deactivate()


@pytest.mark.parametrize(
    "hours,expected",
    [
        (1, "1 Stunde"),
        (24, "24 Stunden"),
        (36, "36 Stunden"),
        (36.5, "36 Stunden und 30 Minuten"),
        (168, "168 Stunden"),
    ],
)
def test_german_reward_and_expiry_do_not_round_to_days(hours, expected):
    humanize.activate("de_DE")
    reward = timedelta(hours=hours)
    message = utils.format_player_message(
        GERMAN_MESSAGE, reward, NOW + reward, language="de_DE"
    )
    assert f"Deine VIP-Belohnung: {expected}." in message
    assert f"Dein VIP läuft in {expected} ab." in message
    assert "ein Tag" not in message
    assert "ab jetzt" not in message


def test_existing_vip_expiry_is_not_confused_with_reward_duration():
    humanize.activate("de_DE")
    message = utils.format_player_message(
        GERMAN_MESSAGE,
        timedelta(hours=36),
        NOW + timedelta(hours=84),
        language="de_DE",
    )
    assert "VIP-Belohnung: 36 Stunden." in message
    assert "VIP läuft in 84 Stunden ab." in message


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "jetzt"), (15, "jetzt"), (60, "in 1 Minute"), (-3600, "vor 1 Stunde")],
)
def test_german_relative_time_handles_now_and_past(seconds, expected):
    humanize.activate("de_DE")
    assert (
        utils.format_player_message(
            "{vip_expiration}",
            timedelta(),
            NOW + timedelta(seconds=seconds),
            language="de-DE",
        )
        == expected
    )


def test_notice_rendering_delay_does_not_produce_fractional_minutes():
    humanize.activate("de_DE")
    assert (
        utils.format_player_message(
            "{vip_expiration}",
            timedelta(hours=36),
            NOW + timedelta(hours=36) - timedelta(seconds=2),
            language="de_DE",
        )
        == "in 36 Stunden"
    )


def test_english_formatting_keeps_tense_and_precise_duration():
    assert (
        utils.format_player_message(
            "Reward: {vip_reward}. Expires: {vip_expiration}.",
            timedelta(hours=36),
            NOW + timedelta(hours=36),
            language="en_US",
        )
        == "Reward: 36 hours. Expires: 36 hours from now."
    )
    assert (
        utils.format_player_message(
            "{vip_expiration}",
            timedelta(),
            NOW - timedelta(hours=2),
            language="en_US",
        )
        == "2 hours ago"
    )


def test_other_locales_retain_translated_duration_and_tense():
    humanize.activate("fr_FR")
    assert (
        utils.format_player_message(
            "{vip_reward}", timedelta(hours=36), NOW, language="fr_FR"
        )
        == "36 heures"
    )
    future = utils.format_player_message(
        "{vip_expiration}", timedelta(), NOW + timedelta(hours=36), language="fr_FR"
    )
    assert "36 heures" in future
    assert "from now" not in future


def test_raw_duration_and_iso_date_options_are_unchanged():
    reward = timedelta(hours=36)
    expiry = NOW + reward
    assert (
        utils.format_player_message(
            "{vip_reward} | {vip_expiration}",
            reward,
            expiry,
            nice_time_delta=False,
            nice_expiration_date=False,
        )
        == f"{reward} | {expiry.isoformat()}"
    )


def test_naive_expiry_remains_supported():
    assert (
        utils.format_player_message(
            "{vip_expiration}",
            timedelta(hours=36),
            (NOW + timedelta(hours=36)).replace(tzinfo=None),
            language="en_US",
        )
        == "36 hours from now"
    )


def test_timezone_offset_does_not_change_remaining_duration():
    expiry = (NOW + timedelta(hours=36)).astimezone(timezone(timedelta(hours=2)))
    message = utils.format_player_message(
        "{vip_expiration}", timedelta(hours=36), expiry, language="en_US"
    )
    assert message == "36 hours from now"


def test_message_delivery_passes_server_language_without_granting_vip():
    humanize.activate("de_DE")
    config = SeedVIPUserConfig(language="de_DE", dry_run=False)
    config.reward.timeframe.days = 0
    config.reward.timeframe.hours = 36
    api, outbox = Mock(), Mock()
    utils.message_players(
        api,
        config,
        GERMAN_MESSAGE,
        ["test-player"],
        {"test-player": NOW + timedelta(hours=36)},
        outbox,
    )
    message = outbox.enqueue.call_args.args[0]["test-player"]
    assert "VIP-Belohnung: 36 Stunden." in message
    assert "VIP läuft in 36 Stunden ab." in message
    api.add_vip.assert_not_called()
    assert config.reward.timeframe.as_timedelta == timedelta(hours=36)
