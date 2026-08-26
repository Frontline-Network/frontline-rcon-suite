import datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from rcon.log_queries import server_time_bounds, server_time_order
from rcon.models import LogLine


def _compile(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_server_time_bounds_compile_to_composite_index_range():
    statement = (
        select(LogLine.id)
        .where(*server_time_bounds("1"))
        .order_by(*server_time_order(descending=True))
        .limit(1000)
    )

    sql = _compile(statement)

    assert "(log_lines.server, log_lines.event_time) >= ('1', '0001-01-01" in sql
    assert "(log_lines.server, log_lines.event_time) <= ('1', '9999-12-31" in sql
    assert "ORDER BY log_lines.server DESC, log_lines.event_time DESC" in sql


def test_server_time_bounds_preserve_requested_time_window_and_order():
    from_ = datetime.datetime(2026, 8, 26, 12, 0, 0)
    till = datetime.datetime(2026, 8, 26, 13, 0, 0)
    statement = (
        select(LogLine.id)
        .where(*server_time_bounds(4, from_, till))
        .order_by(*server_time_order(descending=False))
    )

    sql = _compile(statement)

    assert "(log_lines.server, log_lines.event_time) >= ('4', '2026-08-26 12:00:00')" in sql
    assert "(log_lines.server, log_lines.event_time) <= ('4', '2026-08-26 13:00:00')" in sql
    assert "ORDER BY log_lines.server ASC, log_lines.event_time ASC" in sql
