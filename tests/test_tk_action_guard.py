import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from rcon.automods import tk_action_guard as guard


def test_old_event_cannot_move_transition_into_past():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    assert guard._transition_boundary(100) >= now_ms + 60000
    assert guard._transition_boundary(now_ms + 120000) == now_ms + 120000


@pytest.fixture
def database(monkeypatch):
    engine = create_engine('sqlite://')
    guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(guard, '_transition_boundary', lambda event: event)
    yield maker
    engine.dispose()


def test_cutover_skips_existing_session_and_persists(database):
    assert guard.reserve(3, 'player', 100, 110) is None
    assert guard.reserve(3, 'player', 100, 120) is None
    token = guard.reserve(3, 'player', 121, 125)
    assert token and token.startswith('tk-')
    assert guard.reserve(3, 'player', 121, 126) is None


def test_confirmed_session_is_not_replayed_but_later_session_can_act(database):
    guard.reserve(3, 'seed', 100, 110)
    token = guard.reserve(3, 'player', 120, 130)
    assert guard.finish(3, 'player', token, 'confirmed') == 1
    assert guard.reserve(3, 'player', 120, 140) is None
    assert guard.reserve(3, 'player', 150, 160)


def test_uncertain_action_blocks_later_sessions_until_audited_review(database):
    guard.reserve(3, 'seed', 100, 110)
    token = guard.reserve(3, 'player', 120, 130)
    assert guard.reserve(3, 'player', 150, 160) is None
    assert guard.list_pending(4)['results'] == []
    row = guard.list_pending(3)['results'][0]
    assert row['token'] == token and row['actions'][0]['action'] == 'ban'
    with pytest.raises(ValueError):
        guard.review(3, 'player', token, 'admin', ' ')
    assert guard.review(3, 'player', token, 'admin', 'checked game server') == 1
    assert guard.reserve(3, 'player', 150, 160)
    with database() as session:
        events = session.execute(select(guard.history.c.event, guard.history.c.actor, guard.history.c.reason)).all()
    assert ('reviewed', 'admin', 'checked game server') in events


def test_explicit_rejection_can_retry_and_is_recorded(database):
    guard.reserve(3, 'seed', 100, 110)
    token = guard.reserve(3, 'player', 120, 130)
    assert guard.finish(3, 'player', token, 'rejected') == 1
    second = guard.reserve(3, 'player', 120, 140)
    assert second and second != token


def test_server_and_player_are_isolated(database):
    guard.reserve(3, 'seed', 100, 110)
    guard.reserve(4, 'seed', 100, 110)
    assert guard.reserve(3, 'one', 120, 130)
    assert guard.reserve(3, 'two', 120, 130)
    assert guard.reserve(4, 'one', 120, 130)


@pytest.mark.parametrize('player,connection,event', [('', 100, 110), ('*', 100, 110), ('p', 0, 110), ('p', 120, 110)])
def test_invalid_reservation_is_rejected(database, player, connection, event):
    with pytest.raises(ValueError):
        guard.reserve(3, player, connection, event)
