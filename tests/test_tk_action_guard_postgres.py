import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from rcon.automods import tk_action_guard as guard


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires disposable PostgreSQL')
    root = create_engine(dsn)
    schema = 'tk_guard_' + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'}, pool_size=10)
    guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(guard, '_transition_boundary', lambda event: event)
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


@pytest.mark.parametrize('iteration', range(5))
def test_concurrent_workers_reserve_same_session_once(database, iteration):
    server = 3
    guard.reserve(server, 'initial', 100, 110)
    barrier = Barrier(8)
    def worker(_):
        barrier.wait(timeout=10)
        return guard.reserve(server, 'synthetic-player', 120, 130)
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(worker, range(8)))
    assert sum(token is not None for token in tokens) == 1
    assert len(guard.list_pending(server)['results']) == 1


def test_unconfirmed_action_survives_database_reconnect(database):
    guard.reserve(3, 'initial', 100, 110)
    token = guard.reserve(3, 'synthetic-player', 120, 130)
    database.kw['bind'].dispose()
    assert guard.reserve(3, 'synthetic-player', 140, 150) is None
    assert guard.review(3, 'synthetic-player', token, 'admin', 'checked server') == 1
    assert guard.reserve(3, 'synthetic-player', 140, 150)
