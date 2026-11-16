from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import hooks
from rcon.types import GameEnum, WindowsStoreIdActionType


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
    rcon.get_detailed_player_info.return_value = {'player_id': 'fake-eos-id', 'platform': platform}
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
    rcon.get_detailed_player_info.return_value = {'player_id': 'fake-eos-id', 'platform': platform}
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
    rcon.get_detailed_player_info.return_value = {'player_id': 'fake-eos-id', 'platform': 'PC_WinGDK'}
    getattr(rcon, method).return_value = True
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    kwargs = {'player_id': 'fake-eos-id', 'reason': 'reason', 'by': 'admin'}
    if method == 'temp_ban':
        kwargs['duration_hours'] = 1
    getattr(rcon, method).assert_called_once_with(**kwargs)
    audit.assert_called_once()


@pytest.mark.parametrize('response', [None, {}, {'player_id': 'other', 'platform': 'PC_WinGDK'}])
def test_missing_or_wrong_player_details_never_trigger_rule(monkeypatch, response):
    config = SimpleNamespace(enabled=True, action=WindowsStoreIdActionType.perma_ban,
                             player_message='reason', audit_message='{name}', audit_message_author='admin',
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    monkeypatch.setattr(hooks, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon.get_detailed_player_info.return_value = response
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.perma_ban.assert_not_called()


def test_platform_lookup_failure_never_triggers_rule(monkeypatch):
    config = SimpleNamespace(enabled=True)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon.get_detailed_player_info.side_effect = TimeoutError('offline')
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize('player_id', [None, '', ' '])
def test_missing_identity_never_triggers_a_lookup_or_action(monkeypatch, player_id):
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, 'load_from_db',
                        lambda: SimpleNamespace(windows_store_players=SimpleNamespace(enabled=True)))
    rcon = Mock()
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', player_id)
    rcon.get_detailed_player_info.assert_not_called()
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
    rcon.get_detailed_player_info.return_value = {'player_id': 'fake-eos-id', 'platform': 'PC_WinGDK'}
    rcon.kick.return_value = accepted
    hooks.windows_store_player_check.__wrapped__(rcon, {}, 'player', 'fake-eos-id')
    rcon.kick.assert_called_once()
    audit.assert_not_called()
