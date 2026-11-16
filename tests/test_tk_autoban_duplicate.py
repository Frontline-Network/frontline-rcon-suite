from unittest.mock import Mock
from datetime import datetime, timedelta, timezone

import pytest

from rcon import blacklist
from rcon.automods import tk_autoban
from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig


def test_only_one_ban_for_multiple_teamkills_in_one_history_scan(monkeypatch):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000, 'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
    first = {'action': 'TEAM KILL', 'timestamp_ms': 101000, 'player_name_1': 'synthetic',
             'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'weapon': 'rifle'}
    second = {**first, 'timestamp_ms': 102000}
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [second, first, connected]})
    ban = Mock(return_value={'id': 1})
    audit = Mock()
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, blacklist_id=1, teamkill_tolerance_count=0)
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, second, config=config)
    ban.assert_called_once()
    audit.assert_called_once()
    assert 'enforcement pending' in audit.call_args.kwargs['message']


@pytest.mark.parametrize('returned', [False, None, {}])
def test_unconfirmed_ban_is_not_reported_as_success(monkeypatch, returned):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000, 'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
    tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000, 'player_name_1': 'synthetic',
          'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'weapon': 'rifle'}
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [tk, connected]})
    ban = Mock(return_value=returned)
    audit = Mock()
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0)
    assert tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config=config) == returned
    ban.assert_called_once()
    audit.assert_not_called()


def test_lost_ban_response_is_not_retried_or_reported_as_success(monkeypatch):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000, 'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
    tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000, 'player_name_1': 'synthetic',
          'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'weapon': 'rifle'}
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [tk, connected]})
    ban = Mock(side_effect=TimeoutError('lost response'))
    audit = Mock()
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', audit)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0)
    with pytest.raises(TimeoutError):
        tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config=config)
    ban.assert_called_once()
    audit.assert_not_called()


@pytest.mark.parametrize('returned', [True, False])
@pytest.mark.parametrize('temporary', [True, False])
def test_direct_ban_result_is_propagated(returned, temporary):
    rcon = Mock()
    rcon.perma_ban.return_value = returned
    rcon.temp_ban.return_value = returned
    expires = datetime.now(timezone.utc) + timedelta(hours=2) if temporary else None
    assert blacklist.blacklist_or_ban(rcon, None, 'synthetic-id', 'reason', expires_at=expires) is returned


def test_another_player_with_same_name_cannot_trigger_a_ban(monkeypatch):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000,
                 'player_name_1': 'same-name', 'player_id_1': 'target-id'}
    other_tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000,
                'player_name_1': 'same-name', 'player_id_1': 'other-id',
                'player_name_2': 'victim', 'player_id_2': 'victim-id', 'weapon': 'rifle'}
    current = {**other_tk, 'timestamp_ms': 1000000, 'player_id_1': 'target-id'}
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [current, other_tk, connected]})
    ban = Mock(return_value=True)
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0,
                                             max_time_after_connect_minutes=5)
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, current, config=config)
    ban.assert_not_called()


@pytest.mark.parametrize('missing', ['connect', 'kill'])
def test_missing_identity_prevents_automatic_ban(monkeypatch, missing):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000,
                 'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
    kill = {'action': 'KILL', 'timestamp_ms': 100500, 'player_name_1': 'synthetic',
            'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'player_id_2': 'other-id'}
    tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000, 'player_name_1': 'synthetic',
          'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'player_id_2': 'other-id', 'weapon': 'rifle'}
    if missing == 'connect':
        connected['player_id_1'] = None
    else:
        kill['player_id_1'] = None
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [tk, kill, connected]})
    ban = Mock()
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0)
    tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config=config)
    ban.assert_not_called()


def test_same_player_id_remains_valid_after_name_change(monkeypatch):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000,
                 'player_name_1': 'previous-name', 'player_id_1': 'synthetic-id'}
    tk = {'action': 'TEAM KILL', 'timestamp_ms': 101000, 'player_name_1': 'current-name',
          'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'player_id_2': 'other-id', 'weapon': 'rifle'}
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', lambda **_: {'logs': [tk, connected]})
    ban = Mock(return_value=True)
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', Mock())
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0)
    assert tk_autoban.auto_ban_if_tks_right_after_connection(rcon, tk, config=config) is True
    ban.assert_called_once()
