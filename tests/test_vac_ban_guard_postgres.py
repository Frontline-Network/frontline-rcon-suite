"""VAC reservations use only disposable PostgreSQL and fake RCON actions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from rcon.automods import action_guard
from rcon.hooks import ban_if_has_vac_bans
from tests.test_automod_action_guard_postgres import database


def fixtures(blacklist_id=None):
    player = SimpleNamespace(flags=[], steaminfo=SimpleNamespace(bans={
        'VACBanned': True, 'DaysSinceLastBan': 1, 'NumberOfGameBans': 0,
    }))
    config = SimpleNamespace(vac_history_days=40, game_ban_threshhold=0, whitelist_flags=[],
        ban_on_vac_history_reason='VAC {DAYS_SINCE_LAST_BAN}', auto_expire=False, blacklist_id=blacklist_id)
    return player, config


@pytest.mark.parametrize('blacklist_id', [None, 7])
def test_uncertain_result_survives_reconnect_and_blocks_concurrent_requests(database, monkeypatch, blacklist_id):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    player, config = fixtures(blacklist_id)
    action = Mock(side_effect=TimeoutError('synthetic lost response'))
    barrier = Barrier(8)

    def worker(_):
        barrier.wait(timeout=10)
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')

    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', action):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(8)))
        action.assert_called_once()
        database.kw['bind'].dispose()
        assert action_guard.pending_players(3, 'VacHistory') == {'synthetic-player'}
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        action.assert_called_once()


@pytest.mark.parametrize('blacklist_id,result', [
    (None, True), (None, False),
    (7, {'id': 42, 'player_id': 'synthetic-player', 'blacklist': {'id': 7}}),
])
def test_explicit_results_release_reservation(database, monkeypatch, blacklist_id, result):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    player, config = fixtures(blacklist_id)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=result) as action:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        assert action_guard.pending_players(3, 'VacHistory') == set()
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        assert action.call_count == 2


def test_global_transition_hold_blocks_until_operator_review(database, monkeypatch):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    player, config = fixtures()
    token = action_guard.reserve(3, '*', ['VacHistory'], 'ban', legacy_global=True)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=True) as action:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        action.assert_not_called()
        assert action_guard.review(3, '*', token, 'operator', 'legacy actions checked') == 1
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        action.assert_called_once()


@pytest.mark.parametrize('blacklist_id,result', [
    (None, None), (7, {}), (7, {'reason': 'missing id'}),
    (7, {'id': 42, 'player_id': 'other', 'blacklist': {'id': 7}}),
    (7, {'id': 42, 'player_id': 'synthetic-player', 'blacklist': {'id': 8}}),
    (7, {'id': True, 'player_id': 'synthetic-player', 'blacklist': {'id': 7}}),
])
def test_ambiguous_result_remains_pending(database, monkeypatch, blacklist_id, result):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    player, config = fixtures(blacklist_id)
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.blacklist_or_ban', return_value=result) as action:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    action.assert_called_once()
    assert action_guard.pending_players(3, 'VacHistory') == {'synthetic-player'}


def test_reservation_failure_does_not_send_any_action(database, monkeypatch):
    monkeypatch.setattr('rcon.hooks.get_server_number', lambda: 3)
    player, config = fixtures()
    with patch('rcon.hooks.VacGameBansUserConfig.load_from_db', return_value=config), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.get_player', return_value=player), \
         patch('rcon.hooks.action_guard.reserve', side_effect=RuntimeError('database unavailable')), \
         patch('rcon.hooks.blacklist_or_ban') as action:
        ban_if_has_vac_bans(Mock(), 'synthetic-player', 'synthetic-name')
    action.assert_not_called()
