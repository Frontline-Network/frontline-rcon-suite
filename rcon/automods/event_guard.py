"""Persist event identities for automated actions triggered by game logs.

The caller updates these rows in the same transaction as the general automod
reservation. A pending outcome is never expired automatically.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Integer, MetaData, String, Table, delete, exists, select, update

from rcon.models import get_session_maker

metadata = MetaData()
cutover = Table(
    'automod_event_cutover', metadata,
    Column('server_number', Integer, primary_key=True),
    Column('boundary_ms', BigInteger, nullable=False),
    Column('cleanup_ms', BigInteger, nullable=False),
    CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_automod_event_cutover_server'),
)
events = Table(
    'automod_event_action', metadata,
    Column('server_number', Integer, primary_key=True),
    Column('player_id', String(100), primary_key=True),
    Column('event_key', String(64), primary_key=True),
    Column('rule', String(150), primary_key=True),
    Column('action', String(20), primary_key=True),
    Column('event_ms', BigInteger, nullable=False, index=True),
    Column('token', String(32), nullable=False, index=True),
    Column('state', String(20), nullable=False),
    Column('updated_at', DateTime(timezone=True), nullable=False),
    CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_automod_event_action_server'),
    CheckConstraint("action IN ('message', 'punish', 'kick')", name='ck_automod_event_action_kind'),
    CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name='ck_automod_event_action_state'),
)


def identity(log: dict) -> tuple[int, str]:
    """Use the same event identity as the upstream log deduplicator."""
    timestamp = log.get('timestamp_ms')
    line = log.get('line_without_time')
    if (not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp <= 0
            or not isinstance(line, str) or not line.strip()):
        raise ValueError('Automod event has no reliable identity')
    digest = hashlib.sha256(f'{timestamp}|{line}'.encode('utf-8')).hexdigest()
    return timestamp, digest


def allow_after_cutover(server_number: int, event_ms: int, lock) -> bool:
    """Establish a conservative boundary before processing historical logs.

    The first event establishes a one-minute transition hold. Events more than
    a minute ahead of the local clock are rejected until clocks agree.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # The upstream log loop requests at most three hours of history. Reject
    # events older than a day so expired deduplication records cannot replay.
    if event_ms > now_ms + 60000 or event_ms < now_ms - 24 * 60 * 60 * 1000:
        return False
    with get_session_maker()() as session, session.begin():
        lock(session, server_number, '*')
        row = session.execute(select(cutover).where(
            cutover.c.server_number == server_number)).mappings().one_or_none()
        if row is None:
            boundary = max(now_ms + 60000, event_ms + 60000)
            session.execute(cutover.insert().values(server_number=server_number, boundary_ms=boundary, cleanup_ms=now_ms))
        else:
            boundary = row['boundary_ms']
            if now_ms - row['cleanup_ms'] >= 24 * 60 * 60 * 1000:
                from rcon.automods.action_guard import action_guard_history
                session.execute(delete(events).where(events.c.server_number == server_number,
                    events.c.event_ms < now_ms - 7 * 24 * 60 * 60 * 1000,
                    events.c.state != 'pending',
                    ~exists(select(action_guard_history.c.id).where(
                        action_guard_history.c.server_number == events.c.server_number,
                        action_guard_history.c.player_id == events.c.player_id,
                        action_guard_history.c.token == events.c.token,
                        action_guard_history.c.event == 'reserved',
                        action_guard_history.c.reason.like('periodic:%')))))
                session.execute(update(cutover).where(cutover.c.server_number == server_number).values(cleanup_ms=now_ms))
        return event_ms > boundary
