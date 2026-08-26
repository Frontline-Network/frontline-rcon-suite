import datetime

from sqlalchemy import tuple_

from rcon.models import LogLine


def server_time_bounds(
    server: str | int,
    from_: datetime.datetime | None = None,
    till: datetime.datetime | None = None,
):
    """Return an index-friendly, exact server/time range for log queries.

    PostgreSQL can misestimate ``server = ? ORDER BY event_time`` when one
    server owns most historical rows but is less active at the newest edge of
    the global time index. Expressing the same predicate as a range over the
    composite ``(server, event_time)`` key keeps the server scope exact and
    makes the matching index usable for every server.
    """

    server = str(server)
    lower = from_ if from_ is not None else datetime.datetime.min
    upper = till if till is not None else datetime.datetime.max
    server_time = tuple_(LogLine.server, LogLine.event_time)
    return (
        server_time >= (server, lower),
        server_time <= (server, upper),
    )


def server_time_order(descending: bool):
    """Return the ordering matched by the composite log history index."""

    direction = "desc" if descending else "asc"
    return (
        getattr(LogLine.server, direction)(),
        getattr(LogLine.event_time, direction)(),
    )
