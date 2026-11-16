"""Durable, session-scoped reservations for automatic teamkill bans."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Integer, MetaData, String, Table, Text, UniqueConstraint, select, text, update

from rcon.models import get_session_maker

metadata = MetaData()
cutover = Table(
    'teamkill_ban_cutover', metadata,
    Column('server_number', Integer, primary_key=True),
    Column('event_ms', BigInteger, nullable=False),
    CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_cutover_server'),
)
guard = Table(
    'teamkill_ban_guard', metadata,
    Column('server_number', Integer, primary_key=True),
    Column('player_id', String(100), primary_key=True),
    Column('connection_ms', BigInteger, primary_key=True),
    Column('token', String(35), nullable=False),
    Column('state', String(16), nullable=False, index=True),
    Column('updated_at', DateTime(timezone=True), nullable=False),
    Column('reviewed_by', String(150)),
    Column('review_reason', Text),
    CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_guard_server'),
    CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name='ck_tk_guard_state'),
    UniqueConstraint('token', name='uq_tk_guard_token'),
)
history = Table(
    'teamkill_ban_guard_history', metadata,
    Column('id', String(32), primary_key=True),
    Column('server_number', Integer, nullable=False, index=True),
    Column('player_id', String(100), nullable=False),
    Column('token', String(35), nullable=False, index=True),
    Column('event', String(16), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('actor', String(150)),
    Column('reason', Text),
    CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_history_server'),
    CheckConstraint("event IN ('reserved', 'confirmed', 'rejected', 'reviewed')", name='ck_tk_history_event'),
)


def _lock(session, server_number, scope):
    if session.get_bind().dialect.name == 'postgresql':
        key = int.from_bytes(hashlib.sha256(f'tk-ban:{server_number}:{scope}'.encode()).digest()[:8], 'big', signed=True)
        session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': key})


def _validate(server_number, player_id, connection_ms, event_ms):
    if (not 1 <= server_number <= 32 or not isinstance(player_id, str) or not player_id.strip()
            or len(player_id) > 100 or player_id == '*'
            or not isinstance(connection_ms, int) or isinstance(connection_ms, bool)
            or not isinstance(event_ms, int) or isinstance(event_ms, bool)
            or connection_ms <= 0 or event_ms < connection_ms):
        raise ValueError('Invalid teamkill ban reservation')


def _validate_token(server_number, player_id, token):
    if (not 1 <= server_number <= 32 or not isinstance(player_id, str) or not player_id.strip()
            or len(player_id) > 100 or player_id == '*' or not isinstance(token, str)
            or re.fullmatch(r'tk-[0-9a-f]{32}', token) is None):
        raise ValueError('Invalid teamkill ban token')


def _transition_boundary(event_ms: int) -> int:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return max(event_ms, now_ms + 60000)


def ensure_cutover(server_number: int, event_ms: int) -> None:
    """Establish the transition boundary on the first observed teamkill."""
    if (not isinstance(server_number, int) or isinstance(server_number, bool)
            or not 1 <= server_number <= 32 or not isinstance(event_ms, int)
            or isinstance(event_ms, bool) or event_ms <= 0):
        raise ValueError('Invalid teamkill transition boundary')
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, '*')
        existing = session.execute(select(cutover.c.event_ms).where(
            cutover.c.server_number == server_number)).scalar_one_or_none()
        if existing is None:
            # A queued old event must not put the boundary in the past. Add
            # a conservative clock-skew allowance before enabling new sessions.
            session.execute(cutover.insert().values(server_number=server_number,
                event_ms=_transition_boundary(event_ms)))


def reserve(server_number: int, player_id: str, connection_ms: int, event_ms: int) -> str | None:
    """Reserve once per connection; uncertain actions block later sessions too.

    The first observed teamkill creates a persistent cutover. Sessions
    already in progress at that point are skipped because their old actions
    cannot be reliably reconciled. Future connections remain enforceable.
    """
    _validate(server_number, player_id, connection_ms, event_ms)
    now = datetime.now(timezone.utc)
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, '*')
        cutoff = session.execute(select(cutover.c.event_ms).where(
            cutover.c.server_number == server_number)).scalar_one_or_none()
        if cutoff is None:
            session.execute(cutover.insert().values(server_number=server_number,
                event_ms=_transition_boundary(event_ms)))
            return None
        if connection_ms <= cutoff:
            return None
        _lock(session, server_number, player_id)
        rows = session.execute(select(guard).where(
            guard.c.server_number == server_number, guard.c.player_id == player_id,
        ).with_for_update()).mappings().all()
        if any(row['state'] == 'pending' for row in rows):
            return None
        previous = next((row for row in rows if row['connection_ms'] == connection_ms), None)
        if previous is not None and previous['state'] == 'confirmed':
            return None
        token = 'tk-' + uuid.uuid4().hex
        values = dict(token=token, state='pending', updated_at=now, reviewed_by=None, review_reason=None)
        if previous is None:
            session.execute(guard.insert().values(server_number=server_number, player_id=player_id,
                                                  connection_ms=connection_ms, **values))
        else:
            session.execute(update(guard).where(
                guard.c.server_number == server_number, guard.c.player_id == player_id,
                guard.c.connection_ms == connection_ms).values(**values))
        session.execute(history.insert().values(id=uuid.uuid4().hex, server_number=server_number,
            player_id=player_id, token=token, event='reserved', created_at=now))
        return token


def finish(server_number: int, player_id: str, token: str, result: str) -> int:
    _validate_token(server_number, player_id, token)
    if result not in {'confirmed', 'rejected'}:
        raise ValueError('Invalid teamkill ban result')
    now = datetime.now(timezone.utc)
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        changed = session.execute(update(guard).where(
            guard.c.server_number == server_number, guard.c.player_id == player_id,
            guard.c.token == token, guard.c.state == 'pending',
        ).values(state=result, updated_at=now)).rowcount
        if changed:
            session.execute(history.insert().values(id=uuid.uuid4().hex, server_number=server_number,
                player_id=player_id, token=token, event=result, created_at=now))
        return changed


def review(server_number: int, player_id: str, token: str, actor: str, reason: str) -> int:
    _validate_token(server_number, player_id, token)
    if (not isinstance(actor, str) or not actor.strip() or len(actor) > 150
            or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000):
        raise ValueError('An operator and reason are required')
    now = datetime.now(timezone.utc)
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        changed = session.execute(update(guard).where(
            guard.c.server_number == server_number, guard.c.player_id == player_id,
            guard.c.token == token, guard.c.state == 'pending',
        ).values(state='reviewed', updated_at=now, reviewed_by=actor.strip(), review_reason=reason.strip())).rowcount
        if changed:
            session.execute(history.insert().values(id=uuid.uuid4().hex, server_number=server_number,
                player_id=player_id, token=token, event='reviewed', created_at=now,
                actor=actor.strip(), reason=reason.strip()))
        return changed


def list_pending(server_number: int, limit: int = 50) -> dict:
    if not 1 <= server_number <= 32 or not 1 <= limit <= 100:
        raise ValueError('Invalid server or pagination')
    with get_session_maker()() as session:
        rows = session.execute(select(guard).where(
            guard.c.server_number == server_number, guard.c.state == 'pending',
        ).order_by(guard.c.updated_at, guard.c.token).limit(limit + 1)).mappings().all()
        return {'results': [{'token': row['token'], 'player_id': row['player_id'],
            'updated_at': row['updated_at'].isoformat(),
            'actions': [{'rule': 'AutoMod_TeamKillAfterConnect', 'action': 'ban'}]}
            for row in rows[:limit]], 'more': len(rows) > limit}
