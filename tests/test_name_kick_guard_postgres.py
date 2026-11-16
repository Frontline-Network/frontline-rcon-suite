"""Exercise name-kick reservations against disposable PostgreSQL only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock, patch

from rcon.auto_kick import apply_name_kick
from rcon.automods import action_guard
from rcon.user_config.name_kicks import NameKickUserConfig
from tests.test_automod_action_guard_postgres import database


def test_uncertain_kick_survives_reconnect_and_blocks_parallel_attempts(database, monkeypatch):
    monkeypatch.setattr('rcon.auto_kick.get_server_number', lambda: 3)
    config = NameKickUserConfig(regular_expressions=['invalid'])
    api = Mock()
    api.kick.side_effect = TimeoutError('synthetic lost response')
    barrier = Barrier(8)

    def worker(_):
        barrier.wait(timeout=10)
        return apply_name_kick(api, 'invalid', 'synthetic-player', config)

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(worker, range(8))) == [False] * 8
    api.kick.assert_called_once()
    database.kw['bind'].dispose()
    assert action_guard.pending_players(3, 'NameKick') == {'synthetic-player'}
    assert not apply_name_kick(api, 'invalid', 'synthetic-player', config)
    api.kick.assert_called_once()


def test_confirmed_and_rejected_results_release_reservation(database, monkeypatch):
    monkeypatch.setattr('rcon.auto_kick.get_server_number', lambda: 3)
    config = NameKickUserConfig(regular_expressions=['invalid'])
    api = Mock()
    api.kick.side_effect = [False, True]
    with patch('rcon.auto_kick.send_to_discord_audit'):
        assert not apply_name_kick(api, 'invalid', 'synthetic-player', config)
        assert action_guard.pending_players(3, 'NameKick') == set()
        assert apply_name_kick(api, 'invalid', 'synthetic-player', config)
        assert action_guard.pending_players(3, 'NameKick') == set()
    assert api.kick.call_count == 2


def test_transition_hold_requires_review_before_name_kicks(database, monkeypatch):
    monkeypatch.setattr('rcon.auto_kick.get_server_number', lambda: 3)
    config = NameKickUserConfig(regular_expressions=['invalid'])
    api = Mock()
    api.kick.return_value = True
    token = action_guard.reserve(3, '*', ['NameKick'], 'kick', legacy_global=True)
    assert not apply_name_kick(api, 'invalid', 'synthetic-player', config)
    api.kick.assert_not_called()
    assert action_guard.review(3, '*', token, 'operator', 'legacy actions checked') == 1
    with patch('rcon.auto_kick.send_to_discord_audit'):
        assert apply_name_kick(api, 'invalid', 'synthetic-player', config)
    api.kick.assert_called_once()
