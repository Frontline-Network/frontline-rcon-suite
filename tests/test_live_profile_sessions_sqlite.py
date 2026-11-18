"""Precise ordering of legacy local sessions on SQLite."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from rcon.player_history import _current_session_summary


def test_legacy_creation_timestamps_are_ordered_with_microseconds():
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('''CREATE TABLE player_sessions (
            id integer PRIMARY KEY, playersteamid_id integer NOT NULL,
            start timestamp, "end" timestamp, start_event_us bigint, end_event_us bigint,
            created timestamp NOT NULL, server_number integer NOT NULL)'''))
        connection.execute(text('''INSERT INTO player_sessions VALUES
            (1, 10, '2026-01-01 10:00:00', NULL, NULL, NULL, '2026-01-01 10:00:00.900000', 1),
            (2, 10, '2026-01-01 09:00:00', '2026-01-01 09:10:00', NULL, NULL, '2026-01-01 10:00:00.100000', 1),
            (3, 11, '2026-01-01 10:00:01', NULL, NULL, NULL, '2026-01-01 10:00:01.000000', 1),
            (4, 11, '2026-01-01 10:00:00', '2026-01-01 10:00:00', NULL, NULL, '2026-01-01 10:00:00.999999', 1),
            (5, 12, '2026-01-01 10:00:00', NULL, NULL, NULL, '2026-01-01 10:00:00.9', 1),
            (6, 12, '2026-01-01 09:00:00', '2026-01-01 09:10:00', NULL, NULL, '2026-01-01 10:00:00.10', 1)'''))
    with Session(engine) as session:
        summaries = _current_session_summary(session, [10, 11, 12], 1)
        assert summaries[10].end is None
        assert summaries[11].end is None
        assert summaries[12].end is None
    engine.dispose()
