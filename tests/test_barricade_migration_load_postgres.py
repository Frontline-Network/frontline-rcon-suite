"""Optional synthetic load check; does not predict live migration duration."""
import os
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


def test_index_build_on_representative_session_count():
    if os.getenv('RUN_SCAN_LOAD_TESTS') != '1' or not os.getenv('TEST_POSTGRES_DSN'):
        pytest.skip('requires explicit disposable PostgreSQL load test')
    engine = create_engine(os.environ['TEST_POSTGRES_DSN'])
    schema = 'scan_load_' + uuid4().hex
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            conn.execute(text('CREATE TABLE player_sessions (id bigint PRIMARY KEY, server_number integer, "end" timestamp, end_event_us bigint)'))
            conn.execute(text('''INSERT INTO player_sessions SELECT n,
                CASE WHEN n <= 135785 THEN 3 WHEN n <= 179312 THEN 4 ELSE 1 END,
                CASE WHEN n <= 2538 THEN NULL ELSE '2020-01-01'::timestamp END, NULL
                FROM generate_series(1,1110000) AS n'''))
        with engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            conn.execute(text("SET LOCAL lock_timeout='2s'"))
            conn.execute(text("SET LOCAL statement_timeout='30s'"))
            started = time.monotonic()
            conn.execute(text('CREATE INDEX ix_scan_all ON player_sessions (server_number,id)'))
            first = time.monotonic() - started
            started = time.monotonic()
            conn.execute(text('CREATE INDEX ix_scan_open ON player_sessions (server_number,id) WHERE "end" IS NULL AND end_event_us IS NULL'))
            second = time.monotonic() - started
            print(f'1,110,000 synthetic sessions: full index {first:.3f}s, open index {second:.3f}s')
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
