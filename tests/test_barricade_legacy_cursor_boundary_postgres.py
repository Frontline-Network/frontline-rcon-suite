"""Isolated evidence for legacy connection snapshot limitations.

Only a disposable schema and synthetic session rows are used.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@pytest.fixture
def db():
    dsn = os.environ.get('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires isolated PostgreSQL')
    admin = create_engine(dsn)
    schema = 'legacy_boundary_' + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'}, pool_size=5)
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE sessions (id bigserial PRIMARY KEY, server_number integer NOT NULL, start_value integer NOT NULL)'))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_plain_connection_snapshot_misclassifies_preconnection_uncommitted_row(db):
    writer = db.connect()
    transaction = writer.begin()
    old = writer.scalar(text('INSERT INTO sessions(server_number,start_value) VALUES (3,100) RETURNING id'))
    try:
        # A connection starts while the earlier insert remains uncommitted.
        with db.begin() as conn:
            baseline = set(conn.scalars(text('SELECT id FROM sessions WHERE server_number=3')))
        assert old not in baseline
        transaction.commit()
        with db.begin() as conn:
            after = set(conn.scalars(text('SELECT id FROM sessions WHERE server_number=3')))
        # Set subtraction alone misclassifies an older, previously invisible
        # insert as a new session, so sending it could repeat an old scan.
        assert after - baseline == {old}
    finally:
        if transaction.is_active:
            transaction.rollback()
        writer.close()


def test_tuple_cursor_skips_late_commit_with_lower_preallocated_id(db):
    slow = db.connect()
    transaction = slow.begin()
    older = slow.scalar(text('INSERT INTO sessions(server_number,start_value) VALUES (3,100) RETURNING id'))
    try:
        with db.begin() as conn:
            newer = conn.scalar(text('INSERT INTO sessions(server_number,start_value) VALUES (3,100) RETURNING id'))
        assert older < newer
        with db.begin() as conn:
            cursor = conn.execute(text('SELECT start_value,id FROM sessions WHERE server_number=3 ORDER BY start_value,id')).one()
        transaction.commit()
        with db.begin() as conn:
            subsequent = conn.execute(text('SELECT id FROM sessions WHERE server_number=3 AND (start_value,id) > (:start,:id)'),
                                      {'start': cursor.start_value, 'id': cursor.id}).all()
        assert subsequent == []
    finally:
        if transaction.is_active:
            transaction.rollback()
        slow.close()


def test_share_boundary_waits_for_preexisting_writer_then_includes_its_row(db):
    writer = db.connect()
    transaction = writer.begin()
    old = writer.scalar(text('INSERT INTO sessions(server_number,start_value) VALUES (3,100) RETURNING id'))
    started, finished = Event(), Event()
    def baseline():
        with db.begin() as conn:
            started.set()
            conn.execute(text("SET LOCAL lock_timeout='3s'"))
            conn.execute(text('LOCK TABLE sessions IN SHARE MODE'))
            rows = set(conn.scalars(text('SELECT id FROM sessions WHERE server_number=3')))
            finished.set()
            return rows
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(baseline)
            assert started.wait(2)
            assert not finished.wait(.2)
            transaction.commit()
            assert old in result.result(timeout=5)
        with db.begin() as conn:
            new = conn.scalar(text('INSERT INTO sessions(server_number,start_value) VALUES (3,100) RETURNING id'))
        assert new != old
    finally:
        if transaction.is_active:
            transaction.rollback()
        writer.close()


def test_share_snapshot_lock_blocks_unrelated_server_session_writer(db):
    snapshot = db.connect()
    transaction = snapshot.begin()
    snapshot.execute(text('LOCK TABLE sessions IN SHARE MODE'))
    started = Event()
    def write_other_server():
        with db.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout='300ms'"))
            started.set()
            conn.execute(text('INSERT INTO sessions(server_number,start_value) VALUES (4,100)'))
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(write_other_server)
            assert started.wait(2)
            with pytest.raises(OperationalError) as error:
                result.result(timeout=3)
        assert error.value.orig.pgcode == '55P03'
    finally:
        transaction.rollback()
        snapshot.close()
