import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from rcon.hooks import ban_if_has_vac_bans


@pytest.fixture(autouse=True)
def fake_vac_guard(monkeypatch):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    monkeypatch.setattr('rcon.hooks.action_guard.reserve', Mock(return_value='synthetic-token'))
    monkeypatch.setattr('rcon.hooks.action_guard.finish', Mock(return_value=1))


@pytest.mark.parametrize('result', [False, None])
def test_unconfirmed_direct_vac_ban_is_not_logged_as_success(result, caplog):
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=False, blacklist_id=None)
    with caplog.at_level(logging.INFO, logger='rcon.hooks'), \
         patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=result):
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    assert 'was banned due VAC history' not in caplog.text
    assert 'not confirmed' in caplog.text


def test_vac_blacklist_record_is_not_reported_as_game_server_ban(caplog):
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=False, blacklist_id=1)
    with caplog.at_level(logging.INFO, logger='rcon.hooks'), \
         patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value={'id': 42}):
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    assert 'was banned due VAC history' not in caplog.text
    assert 'blacklist record' in caplog.text


def test_confirmed_direct_vac_ban_is_reported_as_confirmed(caplog):
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=False, blacklist_id=None)
    with caplog.at_level(logging.INFO, logger='rcon.hooks'), \
         patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=True):
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    assert 'VAC ban confirmed by game server' in caplog.text
