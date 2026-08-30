from unittest.mock import Mock, patch

from rcon.api_commands import RconAPI
from rcon.auto_kick import apply_name_kick, scan_current_players
from rcon.player_history import get_available_player_flags
from rcon.user_config.name_kicks import NameKickUserConfig

UNREADABLE_NAME_PATTERN = r"(^[^a-zA-Z0-9äöüÄÖÜß\[\]]+$)"


def test_roster_scan_kicks_existing_matching_player_without_profile_lookup():
    rcon = Mock()
    rcon.get_player_ids.return_value = [
        ("Гук в Шльопках", "invalid-player"),
        ("[FLN]Biene", "valid-player"),
    ]
    config = NameKickUserConfig(
        regular_expressions=[UNREADABLE_NAME_PATTERN],
        kick_reason="Invalid nickname",
        whitelist_flags=[],
    )

    with (
        patch("rcon.auto_kick.get_player_profile") as get_profile,
        patch("rcon.auto_kick.send_to_discord_audit"),
    ):
        kicked = scan_current_players(rcon, config=config)

    assert kicked == 1
    get_profile.assert_not_called()
    rcon.kick.assert_called_once_with(
        player_name="Гук в Шльопках",
        reason="Invalid nickname",
        by="NAME_KICK",
        player_id="invalid-player",
    )


def test_player_with_whitelist_flag_is_not_kicked():
    rcon = Mock()
    config = NameKickUserConfig(
        regular_expressions=[UNREADABLE_NAME_PATTERN],
        whitelist_flags=["name-filter-exempt"],
    )

    with (
        patch("rcon.auto_kick.get_player_profile", return_value={}) as get_profile,
        patch("rcon.auto_kick.player_has_flag", return_value=True),
    ):
        kicked = apply_name_kick(
            rcon,
            "Гук в Шльопках",
            "whitelisted-player",
            config=config,
        )

    assert kicked is False
    get_profile.assert_called_once_with("whitelisted-player", 0)
    rcon.kick.assert_not_called()


def test_available_player_flags_are_counted_and_sorted_for_form_suggestions():
    session = Mock()
    query = session.query.return_value.filter.return_value.group_by.return_value
    query.all.return_value = [
        ("trusted", 2),
        ("Admin", 5),
        ("name-filter-exempt", 5),
    ]

    with patch("rcon.player_history.enter_session") as enter_session:
        enter_session.return_value.__enter__.return_value = session
        result = get_available_player_flags()

    assert result == [
        {"flag": "Admin", "player_count": 5},
        {"flag": "name-filter-exempt", "player_count": 5},
        {"flag": "trusted", "player_count": 2},
    ]


def test_name_kick_flag_options_use_the_database_catalogue():
    catalogue = [{"flag": "trusted", "player_count": 3}]
    with patch(
        "rcon.api_commands.player_history.get_available_player_flags",
        return_value=catalogue,
    ):
        result = RconAPI.get_available_player_flags(Mock())

    assert result == {"flags": catalogue}


def test_config_save_scans_current_roster_once():
    rcon = Mock()
    rcon._validate_user_config.return_value = None

    with patch("rcon.auto_kick.scan_current_players") as scan_current_players_mock:
        result = RconAPI.set_name_kick_config(
            rcon,
            by="admin",
            config={
                "regular_expressions": [UNREADABLE_NAME_PATTERN],
                "kick_reason": "Invalid nickname",
                "discord_webhook_url": None,
                "whitelist_flags": [],
            },
        )

    assert result is None
    scan_current_players_mock.assert_called_once_with(rcon)


def test_roster_scan_failure_does_not_turn_saved_config_into_failed_request():
    rcon = Mock()
    rcon._validate_user_config.return_value = None

    with patch(
        "rcon.auto_kick.scan_current_players", side_effect=RuntimeError("offline")
    ):
        result = RconAPI.set_name_kick_config(
            rcon,
            by="admin",
            config={
                "regular_expressions": [UNREADABLE_NAME_PATTERN],
                "kick_reason": "Invalid nickname",
                "discord_webhook_url": None,
                "whitelist_flags": [],
            },
        )

    assert result is None
