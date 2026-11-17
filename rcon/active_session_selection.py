"""Select the newest local session before checking whether it remains open."""
from sqlalchemy import BigInteger, cast, func
from rcon.models import PlayerID, PlayerSession


def latest_open_sessions(session, player_ids, server_number):
    if not player_ids:
        return []
    if session.get_bind().dialect.name == 'sqlite':
        created_us = cast(func.strftime('%s', PlayerSession.created), BigInteger) * 1_000_000
    else:
        created_us = cast(func.extract('epoch', PlayerSession.created) * 1_000_000, BigInteger)
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
