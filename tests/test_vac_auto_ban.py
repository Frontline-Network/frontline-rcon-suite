import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from rcon.hooks import ban_if_has_vac_bans, should_ban
from rcon.models import PlayerFlag


@pytest.fixture(autouse=True)
def fake_vac_guard(monkeypatch):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    monkeypatch.setattr('rcon.hooks.action_guard.reserve', Mock(return_value='synthetic-token'))
    monkeypatch.setattr('rcon.hooks.action_guard.finish', Mock(return_value=1))


@pytest.mark.parametrize('flag', ['trusted', {'flag': 'trusted'}, PlayerFlag(flag='trusted')])
def test_whitelisted_flag_prevents_eligible_vac_ban(flag):
    bans = {'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0}
    assert should_ban(bans, float('inf'), 40, [flag], ['trusted']) is False


def test_unreadable_flags_do_not_authorize_automatic_ban():
    bans = {'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0}
    assert should_ban(bans, float('inf'), 40, [object()], ['trusted']) is None


def test_vac_handler_respects_database_flag_before_any_ban():
    player = SimpleNamespace(
        flags=[PlayerFlag(flag='trusted')],
        steaminfo=SimpleNamespace(bans={'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0}),
    )
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=['trusted'])
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban') as ban:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    ban.assert_not_called()


def test_vac_handler_still_processes_confirmed_non_exempt_player():
    player = SimpleNamespace(
        flags=[PlayerFlag(flag='other')],
        steaminfo=SimpleNamespace(bans={'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0}),
    )
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=['trusted'],
                             ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=False,
                             blacklist_id=None)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban') as ban:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    ban.assert_called_once()


def test_missing_flags_fail_closed_only_when_exemptions_are_configured():
    bans = {'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0}
    assert should_ban(bans, float('inf'), 40, None, ['trusted']) is None
    assert should_ban(bans, float('inf'), 40, None, []) is True


@pytest.mark.parametrize('blacklist_id', [None, 1])
@pytest.mark.parametrize('days_since', [40, '40'])
def test_expired_vac_action_does_not_create_a_ban_or_blacklist_record(blacklist_id, days_since):
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': days_since, 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=True, blacklist_id=blacklist_id)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban') as ban:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    ban.assert_not_called()


def test_vac_auto_expiry_accepts_numeric_string_when_time_remains():
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': '39', 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=True, blacklist_id=None)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=True) as ban:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    ban.assert_called_once()
    assert ban.call_args.kwargs['expires_at'] is not None


@pytest.mark.parametrize(
    "bans, max_game_bans, max_days_since_ban, player_flags, whitelist_flags, expected",
    [
        (
            {
                "SteamId": "...",
                "CommunityBanned": False,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 0,
                "NumberOfGameBans": 0,
                "EconomyBan": "none",
            },
            float("inf"),
            1,
            ["🤡"],
            ["🤡"],
            False,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": False,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 0,
                "NumberOfGameBans": 0,
                "EconomyBan": "none",
            },
            float("inf"),
            1,
            [],
            [],
            False,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 0,
                "NumberOfGameBans": 0,
                "EconomyBan": "none",
            },
            float("inf"),
            1,
            [],
            [],
            False,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 0,
                "NumberOfGameBans": 0,
                "EconomyBan": "none",
            },
            float("inf"),
            1,
            [],
            [],
            False,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 5,
                "EconomyBan": "none",
            },
            float("inf"),
            40,
            [],
            [],
            False,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 5,
                "EconomyBan": "none",
            },
            6,
            40,
            [],
            [],
            False,
        ),
    ],
)
def test_should_not_ban(
    bans, max_game_bans, max_days_since_ban, player_flags, whitelist_flags, expected
):
    assert (
        should_ban(
            bans=bans,
            max_game_bans=max_game_bans,
            max_days_since_ban=max_days_since_ban,
            player_flags=player_flags,
            whitelist_flags=whitelist_flags,
        )
        == expected
    )


@pytest.mark.parametrize(
    "bans, max_game_bans, max_days_since_ban, player_flags, whitelist_flags, expected",
    [
        (
            {
                "SteamId": "...",
                "CommunityBanned": False,
                "VACBanned": True,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 0,
                "EconomyBan": "none",
            },
            float("inf"),
            40,
            [],
            [],
            True,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": True,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 5,
                "EconomyBan": "none",
            },
            5,
            4,
            [],
            [],
            True,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": False,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 5,
                "EconomyBan": "none",
            },
            5,
            4,
            [],
            [],
            True,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": True,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 1,
                "EconomyBan": "none",
            },
            1,
            4,
            [],
            [],
            True,
        ),
        (
            {
                "SteamId": "...",
                "CommunityBanned": True,
                "VACBanned": True,
                "NumberOfVACBans": 0,
                "DaysSinceLastBan": 1,
                "NumberOfGameBans": 1,
                "EconomyBan": "none",
            },
            1,
            4,
            [],
            ["🤡"],
            True,
        ),
    ],
)
def test_should_ban(
    bans, max_game_bans, max_days_since_ban, player_flags, whitelist_flags, expected
):
    assert (
        should_ban(
            bans=bans,
            max_game_bans=max_game_bans,
            max_days_since_ban=max_days_since_ban,
            player_flags=player_flags,
            whitelist_flags=whitelist_flags,
        )
        == expected
    )
