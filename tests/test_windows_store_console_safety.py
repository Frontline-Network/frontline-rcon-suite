from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import hooks
from rcon.types import GameEnum, WindowsStoreIdActionType


@pytest.fixture(autouse=True)
def isolated_windows_store_guard(monkeypatch):
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

    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    monkeypatch.setattr(hooks.action_guard, 'reserve', reserve)
    monkeypatch.setattr(hooks.action_guard, 'finish', finish)
    return pending


@pytest.mark.parametrize("action", list(WindowsStoreIdActionType))
@pytest.mark.parametrize("player_id", ["0" * 32, "f" * 32])
def test_hllv_eos_ids_do_not_trigger_windows_store_actions(monkeypatch, action, player_id):
    config = SimpleNamespace(enabled=True, action=action, player_message="reason",
                             audit_message="{name}", audit_message_author="admin",
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, "load_from_db",
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, "send_to_discord_audit", audit)
    rcon = Mock()
    rcon.config.game = GameEnum.HLL_VIETNAM
    hooks.windows_store_player_check.__wrapped__(rcon, {}, "player", player_id)
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize('game', [GameEnum.HLL_WW2, GameEnum.HLL_VIETNAM])
@pytest.mark.parametrize('platform', [None, '', 'xbl', 'xsx', 'ps5', 'EPlatform::Xbox_SeriesX',
                                       'EPlatform::PS5', 'EPlatform::PC_EGS', 'unknown'])
def test_ambiguous_or_non_windows_platform_never_triggers_actions(monkeypatch, game, platform):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.perma_ban,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon.config.game = game
    rcon._get_adapted_player_info.return_value = {'iD': 'fake-eos-id', 'platform': platform}
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize('game', [GameEnum.HLL_WW2, GameEnum.HLL_VIETNAM])
@pytest.mark.parametrize('platform', ['EPlatform::PC_WinGDK', 'pc_wingdk'])
def test_confirmed_pc_wingdk_can_trigger_rule(monkeypatch, game, platform):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.kick,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    monkeypatch.setattr(hooks, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon.config.game = game
    rcon._get_adapted_player_info.return_value = {'iD': 'fake-eos-id', 'platform': platform}
    rcon.kick.return_value = True
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_called_once_with(player_id='fake-eos-id', player_name='player', reason='reason', by='admin')


@pytest.mark.parametrize('action,method', [(WindowsStoreIdActionType.temp_ban, 'temp_ban'),
                                           (WindowsStoreIdActionType.perma_ban, 'perma_ban')])
def test_confirmed_pc_ban_uses_player_id_and_audits_success(monkeypatch, action, method):
    config = SimpleNamespace(enabled=True, action=action, player_message='reason',
                             audit_message='{name}', audit_message_author='admin', temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon._get_adapted_player_info.return_value = {'iD': 'fake-eos-id', 'platform': 'PC_WinGDK'}
    getattr(rcon, method).return_value = True
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    kwargs = {'player_id': 'fake-eos-id', 'reason': 'reason', 'by': 'admin'}
    if method == 'temp_ban':
        kwargs['duration_hours'] = 1
    getattr(rcon, method).assert_called_once_with(**kwargs)
    audit.assert_called_once()


@pytest.mark.parametrize('response', [None, {}, {'iD': 'other', 'platform': 'PC_WinGDK'}])
def test_missing_or_wrong_player_details_never_trigger_rule(monkeypatch, response):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.perma_ban,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    monkeypatch.setattr(hooks, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon._get_adapted_player_info.return_value = response
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.perma_ban.assert_not_called()


def test_platform_lookup_failure_never_triggers_rule(monkeypatch):
    config = SimpleNamespace(enabled=True)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon._get_adapted_player_info.side_effect = TimeoutError('offline')
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()
    audit.assert_not_called()


def test_fresh_console_platform_wins_over_stale_cached_pc_data(monkeypatch):
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=SimpleNamespace(enabled=True)))
    rcon = Mock()
    rcon.get_detailed_player_info.return_value = {'player_id': 'fake-eos-id', 'platform': 'PC_WinGDK'}
    rcon._get_adapted_player_info.return_value = {'iD': 'fake-eos-id', 'platform': 'EPlatform::PS5'}
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon._get_adapted_player_info.assert_called_once_with('fake-eos-id')
    rcon.get_detailed_player_info.assert_not_called()
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()


@pytest.mark.parametrize('player_id', [None, '', ' '])
def test_missing_identity_never_triggers_a_lookup_or_action(monkeypatch, player_id):
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=SimpleNamespace(enabled=True)))
    rcon = Mock()
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', player_id)
    rcon._get_adapted_player_info.assert_not_called()
    rcon.kick.assert_not_called()


@pytest.mark.parametrize('accepted', [False, None])
def test_unconfirmed_action_does_not_claim_success(monkeypatch, accepted):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.kick,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon._get_adapted_player_info.return_value = {'iD': 'fake-eos-id', 'platform': 'PC_WinGDK'}
    rcon.kick.return_value = accepted
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_called_once()
    audit.assert_not_called()


@pytest.mark.parametrize('action,method', [(WindowsStoreIdActionType.kick, 'kick'),
    (WindowsStoreIdActionType.temp_ban, 'temp_ban'), (WindowsStoreIdActionType.perma_ban, 'perma_ban')])
@pytest.mark.parametrize('result', [None, TimeoutError('synthetic lost response')])
def test_uncertain_action_blocks_next_connection(monkeypatch, isolated_windows_store_guard, action, method, result):
    config = SimpleNamespace(enabled=True, action=action, player_message='reason',
                             audit_message='{name}', audit_message_author='admin', temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'fake-pc-id', 'platform': 'PC_WinGDK'}
    operation = getattr(api, method)
    if isinstance(result, Exception):
        operation.side_effect = result
    else:
        operation.return_value = result
    hooks.windows_store_player_check.__wrapped__(api, {}, 'player', 'fake-pc-id')
    hooks.windows_store_player_check.__wrapped__(api, {}, 'player', 'fake-pc-id')
    operation.assert_called_once()
    assert isolated_windows_store_guard == {'fake-pc-id': 'test-token'}


def test_reservation_failure_does_not_send_windows_store_action(monkeypatch):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.kick,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    monkeypatch.setattr(hooks.action_guard, 'reserve', Mock(side_effect=RuntimeError('unavailable')))
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'fake-pc-id', 'platform': 'PC_WinGDK'}
    hooks.windows_store_player_check.__wrapped__(api, {}, 'player', 'fake-pc-id')
    api.kick.assert_not_called()


def test_explicitly_rejected_windows_store_action_can_be_retried(monkeypatch, isolated_windows_store_guard):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.kick,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    api = Mock()
    api._get_adapted_player_info.return_value = {'iD': 'fake-pc-id', 'platform': 'PC_WinGDK'}
    api.kick.return_value = False
    hooks.windows_store_player_check.__wrapped__(api, {}, 'player', 'fake-pc-id')
    hooks.windows_store_player_check.__wrapped__(api, {}, 'player', 'fake-pc-id')
    assert api.kick.call_count == 2
    assert isolated_windows_store_guard == {}
