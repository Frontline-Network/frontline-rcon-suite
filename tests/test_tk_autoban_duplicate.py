from unittest.mock import Mock

from rcon.automods import tk_autoban
from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig


def test_only_one_ban_for_multiple_teamkills_in_one_history_scan(monkeypatch):
    connected = {'action': 'CONNECTED', 'timestamp_ms': 100000, 'player_name_1': 'synthetic'}
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
