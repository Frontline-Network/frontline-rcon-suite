"""Exercise concurrent transaction visibility against an isolated PostgreSQL DB."""

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def isolated_schema():
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires a disposable PostgreSQL test database")
    engine = create_engine(dsn)
    schema = f"incident_test_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        conn.execute(text("CREATE TABLE admin_incident_event (id SERIAL PRIMARY KEY, label TEXT NOT NULL)"))
        migration_file = Path(__file__).resolve().parents[1] / "alembic/versions/d3650a1b2c3d_order_incident_event_ids.py"
        spec = importlib.util.spec_from_file_location("incident_order_migration", migration_file)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.op = SimpleNamespace(get_bind=lambda: conn, execute=lambda sql: conn.execute(text(sql)))
        migration.upgrade()
    try:
        yield engine, schema, migration
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_parallel_transactions_cannot_commit_higher_event_before_lower(isolated_schema):
    engine, schema, _ = isolated_schema
    release_first = Event()
    first_inserted = Event()
    second_started = Event()
    second_inserted = Event()

    def writer(label, inserted, wait_for=None):
        with engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            if label == "second":
                second_started.set()
            event_id = conn.execute(text("INSERT INTO admin_incident_event(label) VALUES (:label) RETURNING id"), {"label": label}).scalar_one()
            inserted.set()
            if wait_for is not None:
                assert wait_for.wait(5)
            return event_id

    with engine.begin() as conn:
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        initial = conn.execute(text("INSERT INTO admin_incident_event(label) VALUES ('initial') RETURNING id")).scalar_one()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(writer, "first", first_inserted, release_first)
        assert first_inserted.wait(5)
        second = pool.submit(writer, "second", second_inserted)
        assert second_started.wait(5)
        try:
            assert not second_inserted.wait(0.3)
            with engine.begin() as conn:
                conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                cursor = conn.execute(text("SELECT max(id) FROM admin_incident_event")).scalar_one()
                assert cursor == initial
        finally:
            release_first.set()
        first_id, second_id = first.result(timeout=5), second.result(timeout=5)

    assert initial < first_id < second_id
    with engine.begin() as conn:
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        rows = conn.execute(text("SELECT label FROM admin_incident_event WHERE id > :cursor ORDER BY id"), {"cursor": cursor}).scalars().all()
        assert rows == ["first", "second"]


def test_aborted_writer_releases_lock_and_next_writer_remains_visible(isolated_schema):
    engine, schema, _ = isolated_schema
    with engine.connect() as conn:
        transaction = conn.begin()
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        abandoned = conn.execute(text("INSERT INTO admin_incident_event(label) VALUES ('aborted') RETURNING id")).scalar_one()
        transaction.rollback()

    with engine.begin() as conn:
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        visible = conn.execute(text("INSERT INTO admin_incident_event(label) VALUES ('visible') RETURNING id")).scalar_one()
        assert visible > abandoned
        assert conn.execute(text("SELECT label FROM admin_incident_event ORDER BY id")).scalars().all() == ["visible"]


def test_explicit_ids_cannot_bypass_order_and_downgrade_removes_trigger(isolated_schema):
    engine, schema, migration = isolated_schema
    with engine.begin() as conn:
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        event_id = conn.execute(text("INSERT INTO admin_incident_event(id, label) VALUES (999999, 'explicit') RETURNING id")).scalar_one()
        assert event_id != 999999
        migration.op = SimpleNamespace(get_bind=lambda: conn, execute=lambda sql: conn.execute(text(sql)))
        migration.downgrade()
        explicit_id = conn.execute(text("INSERT INTO admin_incident_event(id, label) VALUES (999999, 'after downgrade') RETURNING id")).scalar_one()
        assert explicit_id == 999999
