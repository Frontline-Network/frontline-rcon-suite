"""Real advisory locks/constraints, only against an explicit disposable test DB."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from rcon import population as p
from rcon.population_models import PopulationSample, SeedingSession
from rcon.user_config.population_history import PopulationHistoryUserConfig as Config


@pytest.fixture
def postgres(monkeypatch):
    url = os.getenv("POPULATION_TEST_DB_URL")
    if not url:
        pytest.skip("Set POPULATION_TEST_DB_URL to a disposable PostgreSQL test DB")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    schema = "population_test_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    for model in (PopulationSample, SeedingSession):
        model.__table__.create(scoped)
    factory = sessionmaker(scoped, expire_on_commit=False)

    @contextmanager
    def session():
        with factory.begin() as db:
            yield db

    monkeypatch.setattr(p, "enter_session", session)
    try:
        yield session
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_parallel_recorders_query_and_persist_only_once_then_recover(postgres):
    rcon = Mock()

    def slots():
        time.sleep(0.05)
        return {"current_players": 0, "max_players": 100}

    rcon.get_slots.side_effect = slots
    rcon.get_map.return_value = "foy_warfare"

    def collect(_):
        return p.record_sample(rcon, 1, Config(), clock=lambda: 1800000001)

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(collect, range(8))) == 1
    assert rcon.get_slots.call_count == 1
    assert not collect(0)
    # A new slot after failure remains recordable.
    rcon.get_slots.side_effect = TimeoutError()
    assert p.record_sample(rcon, 1, Config(), clock=lambda: 1800000031)
    rcon.get_slots.side_effect = slots
    assert p.record_sample(rcon, 1, Config(), clock=lambda: 1800000061)
    with postgres() as db:
        assert db.scalar(select(func.count()).select_from(PopulationSample)) == 3


def test_seeding_start_and_end_retries_are_serialized(postgres):
    session_id = uuid4()

    def start(_):
        return p.mark_seeding(1, "start", session_id, "test", 8)

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(start, range(8)))
    assert all(row == rows[0] for row in rows)
    with postgres() as db:
        assert db.scalar(select(func.count()).select_from(SeedingSession)) == 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        ends = list(
            pool.map(lambda _: p.mark_seeding(1, "end", session_id, "test"), range(8))
        )
    assert all(row == ends[0] for row in ends)
