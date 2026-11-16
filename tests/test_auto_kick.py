from unittest.mock import Mock, patch

import pytest

from rcon.api_commands import RconAPI
from rcon.auto_kick import apply_name_kick, scan_current_players
from rcon.player_history import get_available_player_flags
from rcon.user_config.name_kicks import NameKickUserConfig

UNREADABLE_NAME_PATTERN = r"(^[^a-zA-Z0-9äöüÄÖÜß\[\]]+$)"


@pytest.fixture(autouse=True)
def isolated_name_kick_guard(monkeypatch):
    pending = {}

    def reserve(server, player, rules, action):
        if player in pending or '*' in pending:
            return None
        pending[player] = 'test-token'
        return 'test-token'

    def finish(server, player, token, result, *, expected):
        assert pending[player] == token and result in {'confirmed', 'rejected'}
        del pending[player]
        return 1

    monkeypatch.setattr('rcon.auto_kick.get_server_number', lambda: 3)
    monkeypatch.setattr('rcon.auto_kick.action_guard.reserve', reserve)
    monkeypatch.setattr('rcon.auto_kick.action_guard.finish', finish)
    return pending


def test_roster_scan_kicks_existing_matching_player_without_profile_lookup():
    rcon = Mock()
    rcon.kick.return_value = True
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


def test_rejected_name_kick_is_not_counted_or_audited_as_success():
    rcon = Mock()
    rcon.get_player_ids.return_value = [("invalid", "player-id")]
    rcon.kick.return_value = False
    config = NameKickUserConfig(regular_expressions=["invalid"], whitelist_flags=[])
    with patch("rcon.auto_kick.send_to_discord_audit") as audit:
        assert scan_current_players(rcon, config=config) == 0
    rcon.kick.assert_called_once()
    audit.assert_not_called()


def test_player_with_whitelist_flag_is_not_kicked():
    rcon = Mock()
    config = NameKickUserConfig(
        regular_expressions=[UNREADABLE_NAME_PATTERN],
        whitelist_flags=["name-filter-exempt"],
    )

    with (
        patch("rcon.auto_kick.get_player_profile", return_value={"flags": []}) as get_profile,
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


@pytest.mark.parametrize('profile_value', [RuntimeError('database unavailable'), None, {}, {'flags': None}, {'flags': [{}]}])
def test_name_kick_skips_if_exemption_cannot_be_checked(profile_value):
    rcon = Mock()
    config = NameKickUserConfig(regular_expressions=['invalid'], whitelist_flags=['exempt'])
    lookup = {'side_effect': profile_value} if isinstance(profile_value, Exception) else {'return_value': profile_value}
    with patch('rcon.auto_kick.get_player_profile', **lookup), \
            patch('rcon.auto_kick.send_to_discord_audit') as audit:
        assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config=config) is False
    rcon.kick.assert_not_called()
    audit.assert_not_called()


def test_name_kick_still_enforces_when_verified_flags_do_not_match():
    rcon = Mock()
    rcon.kick.return_value = True
    config = NameKickUserConfig(regular_expressions=['invalid'], whitelist_flags=['exempt'])
    with patch('rcon.auto_kick.get_player_profile', return_value={'flags': []}), \
            patch('rcon.auto_kick.send_to_discord_audit'):
        assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config=config) is True
    rcon.kick.assert_called_once()


def test_roster_scan_continues_after_unavailable_exemption_profile():
    rcon = Mock()
    rcon.kick.return_value = True
    rcon.get_player_ids.return_value = [('invalid-one', 'one'), ('invalid-two', 'two')]
    config = NameKickUserConfig(regular_expressions=['invalid'], whitelist_flags=['exempt'])
    with patch('rcon.auto_kick.get_player_profile', side_effect=[RuntimeError('unavailable'), {'flags': []}]), \
            patch('rcon.auto_kick.send_to_discord_audit'):
        assert scan_current_players(rcon, config=config) == 1
    assert rcon.kick.call_args.kwargs['player_id'] == 'two'
    rcon.kick.assert_called_once()


@pytest.mark.parametrize('result', [None, TimeoutError('lost response')])
def test_uncertain_kick_blocks_later_scans(isolated_name_kick_guard, result):
    rcon = Mock()
    rcon.get_player_ids.return_value = [('invalid', 'synthetic-player')]
    if isinstance(result, Exception):
        rcon.kick.side_effect = result
    else:
        rcon.kick.return_value = result
    config = NameKickUserConfig(regular_expressions=['invalid'])
    assert scan_current_players(rcon, config) == 0
    assert scan_current_players(rcon, config) == 0
    rcon.kick.assert_called_once()
    assert isolated_name_kick_guard == {'synthetic-player': 'test-token'}


def test_explicit_rejection_allows_later_attempt(isolated_name_kick_guard):
    rcon = Mock()
    rcon.kick.return_value = False
    config = NameKickUserConfig(regular_expressions=['invalid'])
    assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config) is False
    assert isolated_name_kick_guard == {}
    assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config) is False
    assert rcon.kick.call_count == 2


def test_reservation_failure_never_sends_kick(monkeypatch):
    rcon = Mock()
    monkeypatch.setattr('rcon.auto_kick.action_guard.reserve', Mock(side_effect=RuntimeError('unavailable')))
    assert apply_name_kick(rcon, 'invalid', 'synthetic-player', NameKickUserConfig(regular_expressions=['invalid'])) is False
    rcon.kick.assert_not_called()


def test_failed_finalization_does_not_retry_the_kick(monkeypatch, isolated_name_kick_guard):
    rcon = Mock()
    rcon.kick.return_value = True
    monkeypatch.setattr('rcon.auto_kick.action_guard.finish', Mock(side_effect=RuntimeError('unavailable')))
    config = NameKickUserConfig(regular_expressions=['invalid'])
    with patch('rcon.auto_kick.send_to_discord_audit'):
        assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config) is True
        assert apply_name_kick(rcon, 'invalid', 'synthetic-player', config) is False
    rcon.kick.assert_called_once()
    assert isolated_name_kick_guard == {'synthetic-player': 'test-token'}


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
