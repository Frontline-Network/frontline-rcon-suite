"""Windows Store action reservations against disposable PostgreSQL only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from rcon import hooks
from rcon.automods import action_guard
from rcon.types import WindowsStoreIdActionType
from tests.test_automod_action_guard_postgres import database


@pytest.mark.parametrize('action,method', [(WindowsStoreIdActionType.kick, 'kick'),
    (WindowsStoreIdActionType.temp_ban, 'temp_ban'), (WindowsStoreIdActionType.perma_ban, 'perma_ban')])
def test_concurrent_uncertain_pc_actions_survive_reconnect(database, monkeypatch, action, method):
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    config = SimpleNamespace(enabled=True, action=action, player_message='reason',
        audit_message='{name}', audit_message_author='admin', temp_ban_length_hours=1)
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'synthetic-pc', 'platform': 'PC_WinGDK'}
    operation = getattr(api, method)
    operation.side_effect = TimeoutError('synthetic lost response')
    barrier = Barrier(8)

    def worker(_):
        barrier.wait(timeout=10)
        hooks.windows_store_player_check.__wrapped__(api, {}, 'synthetic-name', 'synthetic-pc')

    with patch.object(hooks.RconServerSettingsUserConfig, 'load_from_db',
                      return_value=SimpleNamespace(windows_store_players=config)), \
         patch.object(hooks, 'send_to_discord_audit'):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(8)))
        operation.assert_called_once()
        database.kw['bind'].dispose()
        assert action_guard.pending_players(3, 'WindowsStore') == {'synthetic-pc'}
        hooks.windows_store_player_check.__wrapped__(api, {}, 'synthetic-name', 'synthetic-pc')
        operation.assert_called_once()


def test_global_hold_blocks_confirmed_pc_until_audited_review(database, monkeypatch):
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.kick, player_message='reason',
        audit_message='{name}', audit_message_author='admin', temp_ban_length_hours=1)
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'synthetic-pc', 'platform': 'PC_WinGDK'}
    api.kick.return_value = True
    token = action_guard.reserve(3, '*', ['WindowsStore'], 'ban', legacy_global=True)
    with patch.object(hooks.RconServerSettingsUserConfig, 'load_from_db',
                      return_value=SimpleNamespace(windows_store_players=config)), \
         patch.object(hooks, 'send_to_discord_audit'):
        hooks.windows_store_player_check.__wrapped__(api, {}, 'synthetic-name', 'synthetic-pc')
        api.kick.assert_not_called()
        assert action_guard.review(3, '*', token, 'operator', 'legacy actions checked') == 1
        hooks.windows_store_player_check.__wrapped__(api, {}, 'synthetic-name', 'synthetic-pc')
        api.kick.assert_called_once()


def test_ps5_never_reserves_or_sends_action(database, monkeypatch):
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.perma_ban)
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'synthetic-console', 'platform': 'EPlatformFamily::PS5'}
    with patch.object(hooks.RconServerSettingsUserConfig, 'load_from_db',
                      return_value=SimpleNamespace(windows_store_players=config)), \
         patch.object(hooks.action_guard, 'reserve', wraps=action_guard.reserve) as reserve:
        hooks.windows_store_player_check.__wrapped__(api, {}, 'synthetic-name', 'synthetic-console')
        reserve.assert_not_called()
    api.perma_ban.assert_not_called()
