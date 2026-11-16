from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from rcon.automods import action_guard, automod, event_guard
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer, PunitionsToApply


@pytest.fixture
def database(monkeypatch):
    engine = create_engine('sqlite://')
    action_guard.metadata.create_all(engine)
    event_guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(action_guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(event_guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, 'audit', Mock())
    yield maker
    engine.dispose()


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def event(timestamp, line='KILL: synthetic'):
    return event_guard.identity({'timestamp_ms': timestamp, 'line_without_time': line})


def open_cutover(database, server=3):
    now = now_ms()
    with database.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=server, boundary_ms=now - 1000, cleanup_ms=now))


def test_event_identity_is_stable_and_requires_original_log_data():
    assert event(100, 'same') == event(100, 'same')
    assert event(100, 'same') != event(101, 'same')
    for log in ({}, {'timestamp_ms': True, 'line_without_time': 'x'},
                {'timestamp_ms': 1, 'line_without_time': ''}):
        with pytest.raises(ValueError):
            event_guard.identity(log)


def test_first_event_establishes_transition_hold(database):
    first = event(now_ms())
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first) is None
    with database() as session:
        boundary = session.execute(select(event_guard.cutover.c.boundary_ms)).scalar_one()
        assert boundary > first[0]
        assert session.execute(select(event_guard.events)).all() == []


def test_confirmed_event_is_not_replayed_but_distinct_event_is_allowed(database):
    open_cutover(database)
    first = event(now_ms(), 'first')
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first)
    assert token
    assert action_guard.finish(3, 'synthetic', token, 'confirmed', expected=1, event_expected=1) == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first) is None
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'kick', event=first) is None
    other_rule = action_guard.reserve(3, 'synthetic', ['other-rule'], 'message', event=first)
    assert other_rule
    assert action_guard.finish(3, 'synthetic', other_rule, 'confirmed', expected=1, event_expected=1) == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now_ms(), 'second'))


def test_rejected_event_can_retry_but_reviewed_event_cannot(database):
    open_cutover(database)
    first = event(now_ms())
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first)
    assert action_guard.finish(3, 'synthetic', token, 'rejected', expected=1, event_expected=1) == 1
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first)
    assert token
    assert action_guard.review(3, 'synthetic', token, 'operator', 'checked') == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=first) is None
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now_ms(), 'new'))


def test_duplicate_no_squad_action_is_sent_only_once(database):
    open_cutover(database)
    player = PunishPlayer(player_id='synthetic', name='synthetic', squad='', team='',
                          details=PunishDetails(author='rule', message='test'))
    server = Mock()
    server.punish.return_value = True
    same_event = event(now_ms())
    automod._do_punitions(server, ActionMethod.PUNISH, [player], [], event=same_event)
    automod._do_punitions(server, ActionMethod.PUNISH, [player], [], event=same_event)
    server.punish.assert_called_once()


def test_on_kill_deduplicates_same_log_but_allows_a_new_event(database, monkeypatch):
    open_cutover(database)
    player = PunishPlayer(player_id='synthetic', name='synthetic', squad='', team='',
                          details=PunishDetails(author='rule', message='test'))
    mod = Mock()
    mod.on_kill.return_value = PunitionsToApply(punish=[player])
    monkeypatch.setattr(automod, 'get_redis_client', lambda: None)
    monkeypatch.setattr(automod, 'is_first_run_done', lambda _: True)
    monkeypatch.setattr(automod, 'enabled_moderators', lambda: [mod])
    server = Mock()
    server.punish.return_value = True
    log = {'timestamp_ms': now_ms(), 'line_without_time': 'KILL: first'}
    automod.on_kill(server, log)
    automod.on_kill(server, log)
    automod.on_kill(server, {**log, 'line_without_time': 'KILL: second'})
    assert server.punish.call_count == 2
    automod.on_kill(server, {'timestamp_ms': now_ms(), 'line_without_time': ''})
    assert server.punish.call_count == 2


def test_untrusted_old_and_future_events_are_not_actioned(database):
    open_cutover(database)
    now = now_ms()
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now - 2 * 86400000)) is None
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now + 120000)) is None


def test_missing_event_reservation_rolls_back_general_confirmation(database):
    open_cutover(database)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now_ms()))
    with database.begin() as session:
        session.execute(delete(event_guard.events))
    with pytest.raises(RuntimeError, match='event rules'):
        action_guard.finish(3, 'synthetic', token, 'confirmed', expected=1)
    with database() as session:
        assert session.execute(select(action_guard.action_guard.c.state)).scalar_one() == 'pending'


def test_missing_event_reservation_prevents_unsafe_manual_release(database):
    open_cutover(database)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event(now_ms()))
    with database.begin() as session:
        session.execute(delete(event_guard.events))
    with pytest.raises(RuntimeError, match='event rules'):
        action_guard.review(3, 'synthetic', token, 'operator', 'checked')
    with database() as session:
        assert session.execute(select(action_guard.action_guard.c.state)).scalar_one() == 'pending'


def test_cleanup_keeps_uncertain_actions_and_old_events_cannot_replay(database):
    now = now_ms()
    with database.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=3, boundary_ms=now - 1000,
            cleanup_ms=now - 2 * 86400000))
        for state in ('pending', 'confirmed', 'reviewed'):
            session.execute(event_guard.events.insert().values(server_number=3, player_id=state,
                event_key=state[0] * 64, rule='rule', action='punish', event_ms=now - 8 * 86400000,
                token=state[0] * 32, state=state, updated_at=datetime.now(timezone.utc)))
    assert event_guard.allow_after_cutover(3, now, action_guard._lock)
    with database() as session:
        assert session.execute(select(event_guard.events.c.state)).scalars().all() == ['pending']
    assert action_guard.reserve(3, 'confirmed', ['rule'], 'punish',
                                event=event(now - 8 * 86400000)) is None
