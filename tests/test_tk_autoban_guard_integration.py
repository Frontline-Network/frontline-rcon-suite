from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rcon.automods import tk_action_guard as guard, tk_autoban
from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig


@pytest.fixture
def scenario(monkeypatch):
    engine = create_engine('sqlite://')
    guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(tk_autoban, 'get_server_number', lambda: '3')
    monkeypatch.setattr(tk_autoban, 'get_player_profile', lambda *_: None)
    audit = Mock()
    monkeypatch.setattr(tk_autoban, 'send_to_discord_audit', audit)
    api = Mock()
    api.get_vip_ids.return_value = []
    config = BanTeamKillOnConnectUserConfig(enabled=True, teamkill_tolerance_count=0)
    events = {'connected': 100000, 'tk': 101000}
    def logs(**_):
        connected = {'action': 'CONNECTED', 'timestamp_ms': events['connected'],
                     'player_name_1': 'synthetic', 'player_id_1': 'synthetic-id'}
        kill = {'action': 'TEAM KILL', 'timestamp_ms': events['tk'], 'player_name_1': 'synthetic',
                'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'player_id_2': 'other-id', 'weapon': 'rifle'}
        return {'logs': [kill, connected]}
    monkeypatch.setattr(tk_autoban, 'get_recent_logs', logs)
    ban = Mock(return_value=True)
    monkeypatch.setattr(tk_autoban, 'blacklist_or_ban', ban)
    with maker.begin() as session:
        session.execute(guard.cutover.insert().values(server_number=3, event_ms=90000))
    yield api, config, events, ban, audit, maker
    engine.dispose()


def invoke(api, config, events):
    event = {'action': 'TEAM KILL', 'timestamp_ms': events['tk'], 'player_name_1': 'synthetic',
             'player_id_1': 'synthetic-id', 'player_name_2': 'other', 'player_id_2': 'other-id', 'weapon': 'rifle'}
    return tk_autoban.auto_ban_if_tks_right_after_connection(api, event, config)


def test_duplicate_event_does_not_repeat_confirmed_ban(scenario):
    api, config, events, ban, audit, maker = scenario
    invoke(api, config, events)
    invoke(api, config, events)
    ban.assert_called_once()
    audit.assert_called_once()
    events.update(connected=200000, tk=201000)
    invoke(api, config, events)
    assert ban.call_count == 2


def test_uncertain_response_blocks_later_session_until_review(scenario):
    api, config, events, ban, audit, maker = scenario
    ban.side_effect = [TimeoutError('lost response'), True]
    assert invoke(api, config, events) is None
    events.update(connected=200000, tk=201000)
    assert invoke(api, config, events) is None
    ban.assert_called_once()
    row = guard.list_pending(3)['results'][0]
    assert guard.review(3, 'synthetic-id', row['token'], 'admin', 'server checked') == 1
    invoke(api, config, events)
    assert ban.call_count == 2
    audit.assert_called_once()


def test_explicit_rejection_can_retry(scenario):
    api, config, events, ban, audit, maker = scenario
    ban.side_effect = [False, True]
    assert invoke(api, config, events) is False
    assert invoke(api, config, events) is True
    assert ban.call_count == 2
    audit.assert_called_once()


def test_unavailable_guard_prevents_any_ban(scenario, monkeypatch):
    api, config, events, ban, audit, maker = scenario
    monkeypatch.setattr(guard, 'reserve', Mock(side_effect=RuntimeError('db unavailable')))
    assert invoke(api, config, events) is None
    ban.assert_not_called()
    audit.assert_not_called()
