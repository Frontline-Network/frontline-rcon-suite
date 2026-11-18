"""Select the newest local session before checking whether it remains open."""
from sqlalchemy import BigInteger, String, cast, func, literal
from rcon.models import PlayerID, PlayerSession


def session_created_microseconds(session):
    """Order legacy UTC creation times without losing fractional precision."""
    if session.get_bind().dialect.name == 'sqlite':
        created_text = cast(PlayerSession.created, String)
        fraction_text = cast(func.substr(created_text, 21, 6), String) + literal('000000')
        fraction = cast(func.substr(fraction_text, 1, 6), BigInteger)
        # Strip the fraction before strftime: SQLite can round .999999 up to
        # the next second, which would otherwise count that fraction twice.
        return (cast(func.strftime('%s', func.substr(created_text, 1, 19)), BigInteger) * 1_000_000
                + func.coalesce(fraction, 0))
    return cast(func.extract('epoch', PlayerSession.created) * 1_000_000, BigInteger)


def latest_open_sessions(session, player_ids, server_number):
    if not player_ids:
        return []
    created_us = session_created_microseconds(session)
    order = func.coalesce(PlayerSession.start_event_us, created_us, -(2**63))
    ranked = (session.query(
        PlayerSession.id.label('session_id'),
        func.row_number().over(partition_by=PlayerSession.player_id_id,
            order_by=(order.desc(), PlayerSession.id.desc())).label('rank'),
    ).join(PlayerID, PlayerSession.player_id_id == PlayerID.id)
        .filter(PlayerID.player_id.in_(player_ids), PlayerSession.server_number == server_number)
        .subquery())
    return (session.query(PlayerID, PlayerSession)
        .join(PlayerSession, PlayerSession.player_id_id == PlayerID.id)
        .join(ranked, ranked.c.session_id == PlayerSession.id)
        .filter(ranked.c.rank == 1, PlayerSession.end.is_(None),
                PlayerSession.end_event_us.is_(None)).all())
