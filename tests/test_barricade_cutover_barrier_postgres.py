"""Isolated proof of a database-ordered scan cutover, not a migration.

The toy schema intentionally models legacy writers as plain SQL and does not
modify production tables. It proves only ordering, not peer identity, delivery,
log completeness, deletion handling, or a complete production rollout.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
import os
import time

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    admin = create_engine(dsn)
    schema = "scan_fence_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=6)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SEQUENCE session_id_seq"))
            conn.execute(text("CREATE SEQUENCE birth_serial_seq"))
            conn.execute(text("CREATE TABLE sessions (id bigint PRIMARY KEY DEFAULT nextval('session_id_seq'), server_number int NOT NULL, start_value bigint)"))
            conn.execute(text("CREATE TABLE session_birth (session_id bigint PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE, server_number int NOT NULL, serial bigint NOT NULL UNIQUE)"))
            conn.execute(text("CREATE TABLE activation (server_number int PRIMARY KEY, boundary bigint NOT NULL)"))
            conn.execute(text("""
                CREATE FUNCTION capture_birth() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM pg_advisory_xact_lock(913271, NEW.server_number);
                    INSERT INTO session_birth(session_id, server_number, serial)
                    VALUES (NEW.id, NEW.server_number, nextval('birth_serial_seq'));
                    RETURN NEW;
                END $$
            """))
            conn.execute(text("CREATE TRIGGER capture_birth AFTER INSERT ON sessions FOR EACH ROW EXECUTE FUNCTION capture_birth()"))
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def activate(engine, server=3):
    """READ COMMITTED and no session row/table locks after advisory lock."""
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '3s'"))
        conn.execute(text("SELECT pg_advisory_xact_lock(913271,:server)"), {"server": server})
        # Deliberately a separate READ COMMITTED statement: it sees any writer
        # that committed while activation was waiting for the advisory lock.
        fence = conn.scalar(text("SELECT coalesce(max(serial),0) FROM session_birth WHERE server_number=:server"), {"server": server})
        conn.execute(text("INSERT INTO activation(server_number,boundary) VALUES (:server,:fence)"), {"server": server, "fence": fence})
        return fence


def test_preallocated_lower_session_id_is_still_new_after_cutover(db):
    with db.begin() as conn:
        earlier_id = conn.scalar(text("SELECT nextval('session_id_seq')"))
        later_id = conn.scalar(text("INSERT INTO sessions(server_number) VALUES (3) RETURNING id"))
    fence = activate(db)
    with db.begin() as conn:
        conn.execute(text("INSERT INTO sessions(id,server_number) VALUES (:id,3)"), {"id": earlier_id})
        rows = {row.session_id: row.serial for row in conn.execute(text("SELECT session_id,serial FROM session_birth"))}
    assert earlier_id < later_id
    assert rows[later_id] <= fence < rows[earlier_id]


def test_inflight_legacy_writer_commits_before_activation_snapshot(db):
    writer = db.connect()
    tx = writer.begin()
    writer.execute(text("INSERT INTO sessions(server_number) VALUES (3)"))
    started, done = Event(), Event()
    def run_activation():
        started.set()
        try:
            return activate(db)
        finally:
            done.set()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(run_activation)
            assert started.wait(2)
            assert not done.wait(.2)
            tx.commit()
            fence = result.result(timeout=5)
        with db.connect() as conn:
            assert conn.scalar(text("SELECT serial FROM session_birth")) <= fence
    finally:
        if tx.is_active:
            tx.rollback()
        writer.close()


def test_rollback_does_not_create_a_false_birth_or_block_future_insert(db):
    with db.connect() as conn:
        tx = conn.begin()
        conn.execute(text("INSERT INTO sessions(server_number) VALUES (3)"))
        tx.rollback()
    fence = activate(db)
    with db.begin() as conn:
        assert conn.scalar(text("SELECT count(*) FROM session_birth")) == 0
        conn.execute(text("INSERT INTO sessions(server_number) VALUES (3)"))
        assert conn.scalar(text("SELECT serial FROM session_birth")) > fence


def test_preexisting_row_update_does_not_become_new_session(db):
    with db.begin() as conn:
        # Simulate a session saved before installing the trigger.
        conn.execute(text("ALTER TABLE sessions DISABLE TRIGGER capture_birth"))
        session_id = conn.scalar(text("INSERT INTO sessions(server_number,start_value) VALUES (3,1) RETURNING id"))
        conn.execute(text("ALTER TABLE sessions ENABLE TRIGGER capture_birth"))
    activate(db)
    with db.begin() as conn:
        conn.execute(text("UPDATE sessions SET start_value=2 WHERE id=:id"), {"id": session_id})
        assert conn.scalar(text("SELECT count(*) FROM session_birth WHERE session_id=:id"), {"id": session_id}) == 0


def test_independent_server_writer_is_not_blocked_by_other_server_fence(db):
    conn = db.connect()
    tx = conn.begin()
    conn.execute(text("SELECT pg_advisory_xact_lock(913271,3)"))
    def write_server4():
        with db.begin() as other:
            other.execute(text("SET LOCAL lock_timeout = '2s'"))
            return other.scalar(text("INSERT INTO sessions(server_number) VALUES (4) RETURNING id"))
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(write_server4).result(timeout=3) > 0
    finally:
        tx.rollback()
        conn.close()


def test_stale_repeatable_read_snapshot_must_not_be_used_for_activation(db):
    """Negative control: waiting for the writer does not refresh an old snapshot."""
    writer = db.connect()
    writer_tx = writer.begin()
    writer.execute(text("INSERT INTO sessions(server_number) VALUES (3)"))
    snapshot_taken = Event()

    def stale_activation():
        with db.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL lock_timeout = '3s'"))
                assert conn.scalar(text("SELECT count(*) FROM session_birth")) == 0
                snapshot_taken.set()
                conn.execute(text("SELECT pg_advisory_xact_lock(913271,3)"))
                return conn.scalar(text("SELECT coalesce(max(serial),0) FROM session_birth"))

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(stale_activation)
            assert snapshot_taken.wait(2)
            writer_tx.commit()
            assert result.result(timeout=5) == 0
        with db.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM session_birth")) == 1
    finally:
        if writer_tx.is_active:
            writer_tx.rollback()
        writer.close()


def test_backup_share_lock_and_writer_complete_after_activation(db):
    """Model backup table lock while an old INSERT waits for the cutover."""
    activation = db.connect()
    activation_tx = activation.begin()
    activation.execute(text("SELECT pg_advisory_xact_lock(913271,3)"))
    writer_started = Event()
    backup_started = Event()
    pids = {}

    def writer():
        with db.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            pids['writer'] = conn.scalar(text("SELECT pg_backend_pid()"))
            writer_started.set()
            conn.execute(text("INSERT INTO sessions(server_number) VALUES (3)"))

    def backup():
        with db.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            pids['backup'] = conn.scalar(text("SELECT pg_backend_pid()"))
            backup_started.set()
            conn.execute(text("LOCK TABLE sessions IN SHARE MODE"))
            return conn.scalar(text("SELECT count(*) FROM sessions"))

    def wait_blocked(pid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            with db.connect() as conn:
                if conn.scalar(text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": pid}):
                    return
            time.sleep(.02)
        pytest.fail(f"backend {pid} did not enter a lock wait")

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            writer_result = pool.submit(writer)
            assert writer_started.wait(2)
            wait_blocked(pids['writer'])
            backup_result = pool.submit(backup)
            assert backup_started.wait(2)
            wait_blocked(pids['backup'])
            # Activation never takes the session table's SHARE or row locks.
            assert activation.scalar(text("SELECT coalesce(max(serial),0) FROM session_birth")) == 0
            activation.execute(text("INSERT INTO activation VALUES (3,0)"))
            activation_tx.commit()
            writer_result.result(timeout=5)
            assert backup_result.result(timeout=5) == 1
    finally:
        if activation_tx.is_active:
            activation_tx.rollback()
        activation.close()
