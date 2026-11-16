from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from sqlalchemy import select

from rcon.automods import action_guard, event_guard
from tests.test_automod_action_guard_postgres import database


def current_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def test_concurrent_first_events_establish_one_cutover_and_are_held(database):
    now = current_ms()
    barrier = Barrier(8)

    def worker(index):
        event = event_guard.identity({'timestamp_ms': now, 'line_without_time': f'KILL: synthetic {index}'})
        barrier.wait(timeout=10)
        return action_guard.reserve(3, f'synthetic-{index}', ['rule'], 'punish', event=event)

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(token is None for token in pool.map(worker, range(8)))
    with database() as session:
        rows = session.execute(select(event_guard.cutover)).mappings().all()
        assert len(rows) == 1
        assert rows[0]['boundary_ms'] >= now + 60000
        assert session.execute(select(event_guard.events)).first() is None


@pytest.mark.parametrize('iteration', range(5))
def test_concurrent_duplicate_event_reserves_once(database, iteration):
    now = current_ms()
    with database.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=3, boundary_ms=now - 1000, cleanup_ms=now))
    event = event_guard.identity({'timestamp_ms': now, 'line_without_time': 'KILL: synthetic'})
    barrier = Barrier(8)
    def worker(_):
        barrier.wait(timeout=10)
        return action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event)
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(worker, range(8)))
    assert sum(token is not None for token in tokens) == 1
    token = next(token for token in tokens if token)
    assert action_guard.finish(3, 'synthetic', token, 'confirmed', expected=1, event_expected=1) == 1
    database.kw['bind'].dispose()
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event) is None


def test_pending_event_is_reviewable_and_same_event_stays_blocked(database):
    now = current_ms()
    with database.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=3, boundary_ms=now - 1000, cleanup_ms=now))
    event = event_guard.identity({'timestamp_ms': now, 'line_without_time': 'KILL: synthetic'})
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event)
    assert action_guard.list_pending(3)['results'][0]['token'] == token
    assert action_guard.review(3, 'synthetic', token, 'operator', 'checked') == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'punish', event=event) is None
    with database() as session:
        assert session.execute(select(event_guard.events.c.state)).scalar_one() == 'reviewed'
