"""Cross-server live session selection on isolated PostgreSQL."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from rcon.player_history import _current_session_summary, _current_playtime_seconds


def test_local_latest_session_and_global_count_on_postgres():
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "live_sessions_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            connection.execute(text("""CREATE TABLE player_sessions (
                id integer PRIMARY KEY, playersteamid_id integer NOT NULL,
                start timestamp, \"end\" timestamp, start_event_us bigint,
                created timestamp NOT NULL, server_number integer NOT NULL)"""))
            connection.execute(text("""INSERT INTO player_sessions VALUES
                (1, 10, '2026-01-01 10:00', NULL, NULL, '2026-01-01 10:00', 1),
                (2, 10, '2026-01-01 10:20', '2026-01-01 10:25', NULL, '2026-01-01 10:20', 2),
                (3, 11, '2026-01-01 10:00', '2026-01-01 10:15', NULL, '2026-01-01 10:00', 1),
                (4, 11, '2026-01-01 10:20', NULL, NULL, '2026-01-01 10:20', 1)"""))
        with Session(engine) as session:
            local = _current_session_summary(session, [10, 11], 1)
            assert local[10].server_number == 1 and local[10].end is None
            assert local[10].sessions_count == 2
            assert local[11].sessions_count == 2 and local[11].end is None
            assert local[11].start.hour == 10 and local[11].start.minute == 20
            other = _current_session_summary(session, [10], 2)[10]
            assert other.sessions_count == 2 and _current_playtime_seconds(other) == 0
            missing = _current_session_summary(session, [10], 3)[10]
            assert missing.sessions_count == 2 and missing.server_number != 3
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
