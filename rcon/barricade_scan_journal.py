"""Durable reservations for outbound Barricade scans.

Only explicitly registered opt-in websocket peers use this journal. A
reservation is committed before any remote request; an uncertain result is
never retried implicitly.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import get_ident
import asyncio
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, String, TIMESTAMP, UniqueConstraint, and_, func, or_, select, union_all, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base, PlayerID, PlayerSession, get_session_maker
from rcon.vip_rewards.locking import lock

_active_scope = ContextVar('barricade_scan_scope', default=None)


def _current_task():
    try:
        return asyncio.current_task()
    except RuntimeError:
        return None


@dataclass
class _Lease:
    server_number: int
    integration_id: str
    thread: int
    task: object
    active: bool = True


@contextmanager
def delivery_scope(server_number: int, integration_id: str):
    """Hold the database session lock across reservation, send, and result.

    Prototype: synchronous work only. Do not transfer this scope to another
    task or thread; the future async adapter needs its own tested ownership.
    """
    if not 1 <= server_number <= 32 or not integration_id or len(integration_id) > 128:
        raise ValueError('Invalid Barricade scan scope')
    if _active_scope.get() is not None:
        raise RuntimeError('Nested Barricade scan scopes are not supported')
    with lock(f'barricade-scan:{server_number}:{integration_id}'):
        lease = _Lease(server_number, integration_id, get_ident(), _current_task())
        token = _active_scope.set(lease)
        try:
            yield
        finally:
            lease.active = False
            _active_scope.reset(token)


def _require_scope(server_number: int, integration_id: str):
    lease = _active_scope.get()
    if (lease is None or not lease.active or lease.thread != get_ident() or
            lease.task is not _current_task() or
            (lease.server_number, lease.integration_id) != (server_number, integration_id)):
        raise RuntimeError('Barricade scan scope lock is required')


class BarricadeScanDelivery(Base):
    __tablename__ = 'barricade_scan_delivery'
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    integration_id: Mapped[str] = mapped_column(String(128), nullable=False)
    player_session_id: Mapped[int] = mapped_column(nullable=False)
    player_id: Mapped[str] = mapped_column(String(100), nullable=False)
    game: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    review_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint('server_number', 'integration_id', 'player_session_id', name='uq_barricade_scan_session'),
        CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_scan_server'),
        CheckConstraint("game IN ('HLL', 'HLLV')", name='ck_barricade_scan_game'),
        CheckConstraint("status IN ('queued', 'sending', 'done', 'review', 'reviewed')", name='ck_barricade_scan_status'),
    )


class BarricadeScanIntegration(Base):
    """Only explicitly registered credentials may use a durable namespace."""
    __tablename__ = 'barricade_scan_integration'
    server_number: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    credential_id: Mapped[int] = mapped_column(nullable=False)
    # Registration is a proposed activation boundary, not proof that old
    # sessions were previously scanned or that game clocks are synchronized.
    registered_at_us: Mapped[int] = mapped_column(BigInteger, nullable=False)
    __table_args__ = (
        CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_integration_server'),
        CheckConstraint('credential_id > 0', name='ck_barricade_integration_credential'),
    )


class BarricadeScanIntegrationAudit(Base):
    __tablename__ = 'barricade_scan_integration_audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    integration_id: Mapped[str] = mapped_column(String(36), nullable=False)
    old_credential_id: Mapped[int | None] = mapped_column(nullable=True)
    new_credential_id: Mapped[int] = mapped_column(nullable=False)
    actor: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class BarricadeScanReviewAudit(Base):
    __tablename__ = 'barricade_scan_review_audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(nullable=False)
    server_number: Mapped[int] = mapped_column(nullable=False)
    integration_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    actor: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


def classify_activation_start(registered_at_us: int, start_event_us: int | None) -> str:
    """Classify second-resolution log timestamps against a proposed boundary.

    This accounts for lost subsecond precision only. It does not prove that
    the game server and registration host have synchronized clocks, or that
    the server has delivered all its logs. Ambiguous/unknown is not eligible
    for an automatic decision.
    """
    if type(registered_at_us) is not int or registered_at_us < 0:
        raise ValueError('Invalid Barricade registration timestamp')
    if start_event_us is None:
        return 'unknown'
    if (type(start_event_us) is not int or start_event_us < 0 or
            start_event_us % 1_000_000 != 0):
        return 'unknown'
    if start_event_us + 1_000_000 <= registered_at_us:
        return 'before'
    if start_event_us > registered_at_us:
        return 'after'
    return 'ambiguous'


def list_reviews(server_number: int, offset: int = 0, limit: int = 50) -> dict:
    """Read unconfirmed deliveries for one server; caller must authorize access."""
    server_number, offset, limit = int(server_number), int(offset), int(limit)
    if not 1 <= server_number <= 32 or offset < 0 or not 1 <= limit <= 100:
        raise ValueError('Invalid Barricade scan review pagination')
    with get_session_maker()() as session:
        conditions = (BarricadeScanDelivery.server_number == server_number,
                      BarricadeScanDelivery.status == 'review')
        total = session.scalar(select(func.count()).select_from(BarricadeScanDelivery).where(*conditions))
        rows = session.scalars(select(BarricadeScanDelivery).where(*conditions)
                               .order_by(BarricadeScanDelivery.id).offset(offset).limit(limit)).all()
        return {'total': total, 'results': [
            {'id': row.id, 'integration_id': row.integration_id, 'player_id': row.player_id,
             'player_session_id': row.player_session_id, 'game': row.game, 'review_cause': row.review_cause,
             'updated_at': row.updated_at.isoformat()} for row in rows]}


def resolve_review(server_number: int, integration_id: str, delivery_id: int, *, decision: str, actor: str, reason: str):
    """Record an operator decision; the caller must enforce authorization.

    A retry is permitted only after an explicit decision; callers must explain
    that an earlier scan could have completed despite its missing response.
    """
    if (type(delivery_id) is not int or delivery_id <= 0 or decision not in ('confirmed', 'dismissed', 'retry') or
            not isinstance(actor, str) or not actor.strip() or len(actor) > 150 or
            not isinstance(reason, str) or not reason.strip() or len(reason) > 1000):
        raise ValueError('Invalid Barricade scan review')
    with delivery_scope(server_number, integration_id):
        with get_session_maker()() as session, session.begin():
            row = session.scalar(select(BarricadeScanDelivery).where(
                BarricadeScanDelivery.id == delivery_id,
                BarricadeScanDelivery.server_number == server_number,
                BarricadeScanDelivery.integration_id == integration_id).with_for_update())
            if row is None or row.status != 'review':
                raise ValueError('Barricade scan is not awaiting review')
            if row.review_cause == 'session_ended_before_scan' and decision == 'retry':
                raise ValueError('The session ended; an automatic retry cannot verify this session')
            row.status = {'confirmed': 'done', 'dismissed': 'reviewed', 'retry': 'queued'}[decision]
            row.updated_at = datetime.now(timezone.utc)
            session.add(BarricadeScanReviewAudit(delivery_id=delivery_id, server_number=server_number,
                integration_id=integration_id, decision=decision, actor=actor.strip(), reason=reason.strip(),
                created_at=row.updated_at))


def set_integration_credential(server_number: int, integration_id: str, *, expected_credential_id: int | None,
                               new_credential_id: int, actor: str, reason: str):
    """Update a binding under the sender lock; caller must authorize the operator.

    Credential existence and permission validation must happen at the caller's
    authentication boundary. An expected old value prevents stale updates.
    """
    try:
        canonical = str(UUID(integration_id)) == integration_id
    except (ValueError, TypeError, AttributeError):
        canonical = False
    if (not canonical or type(server_number) is not int or not 1 <= server_number <= 32 or
            type(new_credential_id) is not int or new_credential_id <= 0 or
            (expected_credential_id is not None and
             (type(expected_credential_id) is not int or expected_credential_id <= 0)) or
            not isinstance(actor, str) or not actor.strip() or len(actor) > 150 or
            not isinstance(reason, str) or not reason.strip() or len(reason) > 1000):
        raise ValueError('Invalid Barricade integration change')
    with delivery_scope(server_number, f'integration:{integration_id}'):
        with get_session_maker()() as session, session.begin():
            row = session.get(BarricadeScanIntegration, (server_number, integration_id), with_for_update=True)
            old = row.credential_id if row is not None else None
            if old != expected_credential_id:
                raise ValueError('Barricade integration credential changed')
            if old == new_credential_id:
                return False
            if row is None:
                session.add(BarricadeScanIntegration(server_number=server_number, integration_id=integration_id,
                    credential_id=new_credential_id,
                    registered_at_us=int(datetime.now(timezone.utc).timestamp() * 1_000_000)))
            else:
                row.credential_id = new_credential_id
            session.add(BarricadeScanIntegrationAudit(server_number=server_number, integration_id=integration_id,
                old_credential_id=old, new_credential_id=new_credential_id, actor=actor.strip(),
                reason=reason.strip(), created_at=datetime.now(timezone.utc)))
            return True


def credential_is_registered(server_number: int, namespace: str, credential_id: int) -> bool:
    """Check the current binding while holding the same lock as rotation."""
    _require_scope(server_number, namespace)
    if type(credential_id) is not int or credential_id <= 0 or not namespace.startswith('integration:'):
        return False
    ident = namespace.removeprefix('integration:')
    try:
        if str(UUID(ident)) != ident:
            return False
    except (ValueError, TypeError, AttributeError):
        return False
    with get_session_maker()() as session:
        row = session.get(BarricadeScanIntegration, (server_number, ident))
        return row is not None and row.credential_id == credential_id


def registration_boundary(server_number: int, namespace: str, credential_id: int) -> int | None:
    """Read the registered activation boundary for the authenticated key."""
    if (type(server_number) is not int or not 1 <= server_number <= 32 or
            not isinstance(namespace, str) or not namespace.startswith('integration:') or
            type(credential_id) is not int or credential_id <= 0):
        return None
    ident = namespace.removeprefix('integration:')
    try:
        if str(UUID(ident)) != ident:
            return None
    except (ValueError, TypeError, AttributeError):
        return None
    with get_session_maker()() as session:
        row = session.get(BarricadeScanIntegration, (server_number, ident))
        return row.registered_at_us if row is not None and row.credential_id == credential_id else None


def find_unreserved_open_sessions(server_number: int, integration_id: str, *, after_id: int = 0,
                                  limit: int = 100, after_event_us: int | None = None,
                                  include_start: bool = False, player_ids=None):
    """Find candidates without a high-water mark; an open row is not proof of presence.

    The page position is valid only within one traversal; restart from zero
    on every new traversal because lower IDs can commit later. This read must
    be followed by verified presence checks and a reservation.
    Results may change concurrently and must never be treated as exclusive.
    """
    if (not 1 <= server_number <= 32 or not integration_id or len(integration_id) > 128 or
            after_id < 0 or not 1 <= limit <= 1000 or
            (after_event_us is not None and (type(after_event_us) is not int or after_event_us < 0))):
        raise ValueError('Invalid Barricade scan query')
    stmt = (select(PlayerSession.id, PlayerID.player_id, PlayerSession.start_event_us, BarricadeScanDelivery.status)
            .join(PlayerID, PlayerID.id == PlayerSession.player_id_id)
            .outerjoin(BarricadeScanDelivery, and_(
                BarricadeScanDelivery.player_session_id == PlayerSession.id,
                BarricadeScanDelivery.server_number == server_number,
                BarricadeScanDelivery.integration_id == integration_id))
            .where(PlayerSession.server_number == server_number, PlayerSession.end.is_(None),
                   PlayerSession.end_event_us.is_(None), PlayerSession.id > after_id,
                   or_(BarricadeScanDelivery.id.is_(None), BarricadeScanDelivery.status == 'queued'))
            .order_by(PlayerSession.id).limit(limit))
    if after_event_us is not None:
        # Unknown starts are not assumed to be newer than the boundary.
        stmt = stmt.where(PlayerSession.start_event_us > after_event_us)
    if player_ids is not None:
        if (not isinstance(player_ids, (set, frozenset)) or len(player_ids) > 250 or
                any(not isinstance(value, str) or not value or len(value) > 100 for value in player_ids)):
            raise ValueError('Invalid Barricade roster')
        if not player_ids:
            return []
        stmt = stmt.where(PlayerID.player_id.in_(player_ids))
    with get_session_maker()() as session:
        return [(row.id, row.player_id, row.start_event_us, row.status) if include_start else (row.id, row.player_id)
                for row in session.execute(stmt)]


def mark_activation_review(server_number: int, integration_id: str, session_id: int,
                           player_id: str, game: str, cause: str) -> None:
    """Record an ambiguous pre-send candidate; no remote action has occurred."""
    _require_scope(server_number, integration_id)
    if (cause not in ('activation_before', 'activation_ambiguous', 'activation_unknown',
                      'session_ended_before_scan') or
            game not in ('HLL', 'HLLV') or type(session_id) is not int or session_id <= 0 or
            not isinstance(player_id, str) or not 0 < len(player_id) <= 100):
        raise ValueError('Invalid activation review')
    now = datetime.now(timezone.utc)
    stmt = (insert(BarricadeScanDelivery).values(server_number=server_number, integration_id=integration_id,
            player_session_id=session_id, player_id=player_id, game=game, status='review', review_cause=cause,
            created_at=now, updated_at=now).on_conflict_do_nothing(constraint='uq_barricade_scan_session'))
    with get_session_maker()() as session, session.begin():
        session.execute(stmt)
        if cause == 'session_ended_before_scan':
            session.execute(update(BarricadeScanDelivery).where(
                BarricadeScanDelivery.server_number == server_number,
                BarricadeScanDelivery.integration_id == integration_id,
                BarricadeScanDelivery.player_session_id == session_id,
                BarricadeScanDelivery.player_id == player_id,
                BarricadeScanDelivery.game == game,
                BarricadeScanDelivery.status == 'queued').values(
                    status='review', review_cause=cause, updated_at=now))


def find_unreserved_recent_closed_sessions(server_number: int, integration_id: str, boundary_us: int,
                                            *, after_id: int = 0, limit: int = 100):
    """Find recently ended candidates without assuming their scan succeeded."""
    if (type(server_number) is not int or not 1 <= server_number <= 32 or
            not isinstance(integration_id, str) or not 0 < len(integration_id) <= 128 or
            type(boundary_us) is not int or boundary_us < 0 or
            type(after_id) is not int or after_id < 0 or type(limit) is not int or not 1 <= limit <= 1000):
        raise ValueError('Invalid Barricade closed session query')
    floor = boundary_us // 1_000_000 * 1_000_000
    matching_delivery = select(BarricadeScanDelivery.id).where(
        BarricadeScanDelivery.player_session_id == PlayerSession.id,
        BarricadeScanDelivery.server_number == server_number,
        BarricadeScanDelivery.integration_id == integration_id).exists()
    closed = or_(PlayerSession.end.is_not(None), PlayerSession.end_event_us.is_not(None))
    recent = (select(PlayerSession.id.label('session_id'), PlayerID.player_id)
        .join(PlayerID, PlayerID.id == PlayerSession.player_id_id)
        .where(PlayerSession.server_number == server_number, PlayerSession.id > after_id, closed,
            or_(PlayerSession.start_event_us >= floor, PlayerSession.end_event_us >= floor),
            ~matching_delivery))
    queued = (select(PlayerSession.id.label('session_id'), PlayerID.player_id)
        .select_from(BarricadeScanDelivery)
        .join(PlayerSession, PlayerSession.id == BarricadeScanDelivery.player_session_id)
        .join(PlayerID, PlayerID.id == PlayerSession.player_id_id)
        .where(BarricadeScanDelivery.server_number == server_number,
            BarricadeScanDelivery.integration_id == integration_id,
            BarricadeScanDelivery.status == 'queued', PlayerSession.server_number == server_number,
            PlayerSession.id > after_id, closed))
    candidates = union_all(recent, queued).subquery()
    stmt = select(candidates.c.session_id, candidates.c.player_id).order_by(candidates.c.session_id).limit(limit)
    with get_session_maker()() as session:
        return [(row.session_id, row.player_id) for row in session.execute(stmt)]


def reserve(server_number: int, integration_id: str, session_id: int, player_id: str, game: str) -> int | None:
    """Reserve once across processes; None means a reservation already exists."""
    _require_scope(server_number, integration_id)
    if not (1 <= server_number <= 32 and 0 < len(integration_id) <= 128 and
            session_id > 0 and 0 < len(player_id) <= 100 and game in ('HLL', 'HLLV')):
        raise ValueError('Invalid Barricade scan reservation')
    now = datetime.now(timezone.utc)
    stmt = (insert(BarricadeScanDelivery).values(
        server_number=server_number, integration_id=integration_id,
        player_session_id=session_id, player_id=player_id, game=game,
        status='sending', created_at=now, updated_at=now)
        .on_conflict_do_nothing(constraint='uq_barricade_scan_session')
        .returning(BarricadeScanDelivery.id))
    with get_session_maker()() as session, session.begin():
        delivery_id = session.scalar(stmt)
        if delivery_id is None:
            existing = session.scalar(select(BarricadeScanDelivery).where(
                BarricadeScanDelivery.server_number == server_number,
                BarricadeScanDelivery.integration_id == integration_id,
                BarricadeScanDelivery.player_session_id == session_id))
            if existing is None or existing.player_id != player_id or existing.game != game:
                raise ValueError('Conflicting Barricade scan reservation')
            if existing.status == 'queued':
                existing.status = 'sending'
                existing.review_cause = None
                existing.updated_at = now
                return existing.id
        return delivery_id


def finish(delivery_id: int, server_number: int, integration_id: str, *, confirmed: bool) -> bool:
    """Persist confirmation or review; late outcomes cannot overwrite a decision."""
    _require_scope(server_number, integration_id)
    stmt = (update(BarricadeScanDelivery)
            .where(BarricadeScanDelivery.id == delivery_id, BarricadeScanDelivery.status == 'sending',
                   BarricadeScanDelivery.server_number == server_number,
                   BarricadeScanDelivery.integration_id == integration_id)
            .values(status='done' if confirmed else 'review',
                    review_cause=None if confirmed else 'uncertain_delivery', updated_at=datetime.now(timezone.utc))
            .returning(BarricadeScanDelivery.id))
    with get_session_maker()() as session, session.begin():
        return session.scalar(stmt) is not None


def recover_interrupted(server_number: int, integration_id: str) -> int:
    """Mark interrupted sends for review while no sender holds this scope."""
    _require_scope(server_number, integration_id)
    stmt = (update(BarricadeScanDelivery)
            .where(BarricadeScanDelivery.server_number == server_number,
                   BarricadeScanDelivery.integration_id == integration_id,
                   BarricadeScanDelivery.status == 'sending')
            .values(status='review', review_cause='uncertain_delivery', updated_at=datetime.now(timezone.utc))
            .returning(BarricadeScanDelivery.id))
    with get_session_maker()() as session, session.begin():
        return len(session.scalars(stmt).all())
