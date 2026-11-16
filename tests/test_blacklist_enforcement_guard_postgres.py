"""Blacklist enforcement serialization against disposable PostgreSQL only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from rcon import blacklist, hooks
from rcon import blacklist_sync_journal as journal
from rcon.automods import action_guard
from tests.test_automod_action_guard_postgres import database


@pytest.fixture
def configured(database, monkeypatch):
    engine = database.kw['bind']
    monkeypatch.setattr('rcon.models.get_engine', lambda: engine)
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    monkeypatch.setattr(blacklist, 'get_ban_state_from_record', lambda record: blacklist.BanState.PERMA if record else blacklist.BanState.NONE)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    return database


def make_record():
    return SimpleNamespace(admin_name='tester', expires_at=None, get_formatted_reason=lambda: 'reason')


def test_uncertain_action_survives_reconnect_and_blocks_removal(configured):
    api = Mock()
    api.perma_ban.side_effect = TimeoutError('synthetic lost response')
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    configured.kw['bind'].dispose()
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == {'synthetic'}
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    api.perma_ban.assert_called_once()
    with pytest.raises(RuntimeError, match='awaits review'):
        blacklist.synchronize_ban(api, 'synthetic', None, blacklist.BanState.PERMA)
    api.remove_perma_ban.assert_not_called()


def test_rejected_action_can_be_retried(configured):
    api = Mock()
    api.perma_ban.return_value = False
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == set()
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    assert api.perma_ban.call_count == 2


def test_synchronization_waits_for_connect_action_and_does_not_remove_after_timeout(configured):
    api = Mock()
    started, release = Event(), Event()

    def lost_reply(**_kwargs):
        started.set()
        assert release.wait(10)
        raise TimeoutError('synthetic lost response')

    api.perma_ban.side_effect = lost_reply
    record = make_record()
    with patch('rcon.hooks.enter_session'), patch('rcon.hooks.is_player_blacklisted', return_value=record):
        with ThreadPoolExecutor(max_workers=2) as pool:
            connection = pool.submit(hooks.ban_if_blacklisted, api, 'synthetic', 'name')
            assert started.wait(10)
            sync = pool.submit(blacklist.synchronize_ban, api, 'synthetic', None, blacklist.BanState.PERMA)
            release.set()
            assert connection.result(timeout=15) == (True, False)
            with pytest.raises(RuntimeError, match='awaits review'):
                sync.result(timeout=15)
    api.perma_ban.assert_called_once()
    api.remove_perma_ban.assert_not_called()


def test_durable_sync_journal_moves_to_review_when_connect_action_is_uncertain(configured, monkeypatch):
    engine = configured.kw['bind']
    journal.BlacklistSyncDelivery.__table__.create(engine, checkfirst=True)
    monkeypatch.setattr(journal, 'get_session_maker', lambda: configured)
    api = Mock()
    api.perma_ban.side_effect = TimeoutError('synthetic lost response')
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    with configured() as session, session.begin():
        journal.enqueue(session, b'synthetic', 4)
    def handler(_):
        blacklist.synchronize_ban(api, 'synthetic', None, blacklist.BanState.PERMA)
    assert journal.process_one(3, handler) == 'review'
    assert journal.process_one(3, handler) == 'review'
    api.remove_perma_ban.assert_not_called()
    api.perma_ban.assert_called_once()


def test_transition_hold_blocks_actions_until_audited_review(configured):
    api = Mock()
    api.perma_ban.return_value = True
    token = action_guard.reserve(3, '*', ['BlacklistEnforcement'], 'ban', legacy_global=True)
    assert not blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    with pytest.raises(RuntimeError, match='awaits review'):
        blacklist.synchronize_ban(api, 'synthetic', None, blacklist.BanState.PERMA)
    api.perma_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()
    assert action_guard.review(3, '*', token, 'operator', 'legacy actions checked') == 1
    assert blacklist.apply_blacklist_punishment(api, make_record(), 'synthetic', 'name')
    api.perma_ban.assert_called_once()
