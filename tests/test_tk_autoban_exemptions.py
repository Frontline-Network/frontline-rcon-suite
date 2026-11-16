from unittest.mock import Mock

import pytest

from rcon.automods import tk_autoban
from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig, BanTeamKillOnConnectWhiteList


@pytest.fixture
def scenario(monkeypatch):
    monkeypatch.setattr(tk_autoban, 'get_server_number', lambda: '3')
    monkeypatch.setattr(tk_autoban.tk_action_guard, 'ensure_cutover', lambda *_: None)
    monkeypatch.setattr(tk_autoban.tk_action_guard, 'reserve', lambda *_: 'tk-synthetic')
    monkeypatch.setattr(tk_autoban.tk_action_guard, 'finish', lambda *_: 1)
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000,
                 'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
    tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000,
          'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id',
          'player_name_2': 'other', 'player_id_2': 'other-id', 'weapon': 'rifle'}
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [tk, connected]})
    profile = Mock(return_value={'sessions_count': 0, 'flags': []})
    ban = Mock(return_value=True)
    monkeypatch.setattr(tk_autoban, 'get_player_profile', profile)
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0,
        whitelist_players=BanTeamKillOnConnectWhiteList(is_vip=True, has_at_least_n_sessions=2, has_flag=[]))
    return rcon, tk, config, profile, ban


def test_vip_is_exempt_even_when_profile_does_not_exist(scenario):
    rcon, tk, config, profile, ban = scenario
    profile.return_value = None
    rcon.get_vip_ids.return_value = [{'player_id': 'synthetic-id'}]
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_not_called()


@pytest.mark.parametrize('broken', ['vip', 'profile', 'malformed_vip', 'malformed_profile'])
def test_failed_or_incomplete_exemption_check_never_bans(scenario, broken):
    rcon, tk, config, profile, ban = scenario
    if broken == 'vip': rcon.get_vip_ids.side_effect = TimeoutError('offline')
    if broken == 'profile': profile.side_effect = RuntimeError('database offline')
    if broken == 'malformed_vip': rcon.get_vip_ids.return_value = [{}]
    if broken == 'malformed_profile': profile.return_value = {}
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_not_called()


def test_confirmed_non_exempt_player_is_still_processed(scenario):
    rcon, tk, config, profile, ban = scenario
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_called_once()


def test_confirmed_absent_profile_can_be_treated_as_new_player(scenario):
    rcon, tk, config, profile, ban = scenario
    profile.return_value = None
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_called_once()


def test_player_with_sufficient_sessions_is_exempt(scenario):
    rcon, tk, config, profile, ban = scenario
    profile.return_value = {'sessions_count': 2, 'flags': []}
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_not_called()


def test_player_with_whitelist_flag_is_exempt(scenario):
    rcon, tk, config, profile, ban = scenario
    config.whitelist_players.has_flag = ['trusted']
    profile.return_value = {'sessions_count': 0, 'flags': [{'flag': 'trusted'}]}
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_not_called()


def test_missing_flag_list_does_not_bypass_an_enabled_exemption(scenario):
    rcon, tk, config, profile, ban = scenario
    config.whitelist_players.has_flag = ['trusted']
    profile.return_value = {'sessions_count': 0}
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config)
    ban.assert_not_called()
