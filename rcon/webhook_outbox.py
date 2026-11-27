"""Durable webhook payloads; Redis is only a bounded wake-up index.

Claiming is distinct from starting HTTP. Abandoned claims can be retried;
abandoned sends remain reviewable because Discord may already have accepted
them. No database transaction is held while the caller performs network I/O.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import math
import re
from uuid import uuid4

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, LargeBinary,
    String, Text, TIMESTAMP, UniqueConstraint, case, delete, false, func, or_, select, update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base, get_session_maker

ACTIVE = ("queued", "claimed", "sending")
_REASON = re.compile(r"[a-zA-Z0-9_.:-]{1,80}\Z")


class OutboxStorageError(RuntimeError):
    """A sanitized error: underlying SQL parameters can contain webhook tokens."""


class WebhookOutboxQueue(Base):
    __tablename__ = "webhook_outbox_queue"
    queue_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    queue_id: Mapped[str] = mapped_column(Text, nullable=False)
    native_snapshot_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    legacy_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    legacy_review_generation: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class WebhookOutboxDelivery(Base):
    __tablename__ = "webhook_outbox_delivery"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(192))
    queue_hash: Mapped[str] = mapped_column(ForeignKey("webhook_outbox_queue.queue_hash"), nullable=False)
    server_number: Mapped[int | None] = mapped_column(Integer)
    webhook_type: Mapped[str | None] = mapped_column(String(64))
    message_type: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[bytes | None] = mapped_column(LargeBinary)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    source_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    operator_retry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_token: Mapped[str | None] = mapped_column(String(32))
    lease_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    available_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_webhook_outbox_message"),
        UniqueConstraint("dedupe_key", name="uq_webhook_outbox_dedupe"),
        CheckConstraint("status IN ('queued','claimed','sending','sent','review','superseded')", name="ck_webhook_outbox_status"),
        CheckConstraint("priority IN (0,1)", name="ck_webhook_outbox_priority"),
        CheckConstraint("attempts >= 0", name="ck_webhook_outbox_attempts"),
        CheckConstraint("server_number IS NULL OR server_number BETWEEN 1 AND 2147483647", name="ck_webhook_outbox_server"),
        CheckConstraint("status IN ('sent','superseded') OR payload IS NOT NULL", name="ck_webhook_outbox_payload"),
        Index("ix_webhook_outbox_queue_order", "queue_hash", "priority", "id"),
        Index("ix_webhook_outbox_pending", "status", "available_at", "id"),
        Index("ix_webhook_outbox_lease", "status", "lease_until"),
        Index("ix_webhook_outbox_completed", "status", "completed_at", "id"),
    )


@dataclass(frozen=True)
class Claim:
    id: str
    token: str
    payload: bytes = field(repr=False)
    queue_id: str = field(repr=False)
    attempts: int = 0
    server_number: int | None = None
    allow_expired: bool = False


def _safe_storage(func):
    @wraps(func)
    def call(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError:
            # Never expose a StatementError's bound payload/token parameters.
            raise OutboxStorageError("Webhook outbox storage is unavailable") from None
    return call


def _now(now=None):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("An aware outbox timestamp is required")
    return value.astimezone(timezone.utc)


def _bound(limit, maximum=1000):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= maximum:
        raise ValueError("Invalid outbox batch limit")
    return limit


def _seconds(value, maximum=3600):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError("Invalid outbox duration")
    return float(value)


def _queue_hash(queue_id):
    if not isinstance(queue_id, str) or not queue_id or len(queue_id) > 2048:
        raise ValueError("Invalid webhook queue identifier")
    return hashlib.sha256(queue_id.encode()).hexdigest()


def _reason(reason):
    if reason is not None and (not isinstance(reason, str) or not _REASON.fullmatch(reason)):
        raise ValueError("Outbox reasons must be fixed, redacted reason codes")
    return reason


def _queue(session, queue_id, now, *, create=False, skip_locked=False):
    key = _queue_hash(queue_id)
    if create:
        dialect = session.get_bind().dialect.name
        insert = pg_insert if dialect == "postgresql" else sqlite_insert if dialect == "sqlite" else None
        if insert is None:
            raise ValueError("Unsupported webhook outbox database")
        session.execute(insert(WebhookOutboxQueue).values(queue_hash=key, queue_id=queue_id, created_at=now)
                        .on_conflict_do_nothing(index_elements=["queue_hash"]))
    row = session.scalar(select(WebhookOutboxQueue).where(WebhookOutboxQueue.queue_hash == key)
                         .with_for_update(skip_locked=skip_locked))
    if row is not None and row.queue_id != queue_id:
        raise ValueError("Webhook queue hash collision")
    return row


def _status(row):
    """Operator-safe metadata, deliberately excluding queue URLs and payloads."""
    return dict(id=row.message_id, server_number=row.server_number,
                webhook_type=row.webhook_type, message_type=row.message_type,
                status=row.status, retry_attempts=row.attempts, reason=row.reason,
                created_at=_aware(row.created_at), updated_at=_aware(row.updated_at),
                failed_at=_aware(row.completed_at) if row.status == "review" else None)


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


@_safe_storage
def enqueue(queue_id, payload, server_number=None, *, message_id=None, public_id=None,
            dedupe_key=None, message_type=None, webhook_type=None, legacy=False,
            coalesce=False, initial_status="queued", initial_attempts=0,
            reason=None, created_at=None, now=None):
    """Commit a payload before returning its stable public ID.

    A legacy importer must supply a stable *occurrence* key. Identical payloads
    may be separate legitimate messages, so their content hash is not a key.
    """
    now = _now(now)
    if not isinstance(payload, bytes) or (not payload and initial_status != "review"):
        raise ValueError("Webhook outbox requires a nonempty byte payload")
    if server_number is not None and (isinstance(server_number, bool) or not isinstance(server_number, int) or not 1 <= server_number <= 2**31 - 1):
        raise ValueError("Invalid webhook server number")
    if public_id is not None and message_id is not None and public_id != message_id:
        raise ValueError("Conflicting public outbox identifiers")
    message_id = public_id or message_id or uuid4().hex
    if not isinstance(message_id, str) or not 1 <= len(message_id) <= 64:
        raise ValueError("Invalid outbox message identifier")
    if dedupe_key is not None and (not isinstance(dedupe_key, str) or not 1 <= len(dedupe_key) <= 192):
        raise ValueError("Invalid outbox occurrence identifier")
    if message_type is not None and (not isinstance(message_type, str) or len(message_type) > 128):
        raise ValueError("Invalid webhook message type")
    if webhook_type is not None and (not isinstance(webhook_type, str) or len(webhook_type) > 64):
        raise ValueError("Invalid webhook type")
    if not isinstance(legacy, bool) or not isinstance(coalesce, bool) or initial_status not in ("queued", "review"):
        raise ValueError("Invalid webhook admission policy")
    if isinstance(initial_attempts, bool) or not isinstance(initial_attempts, int) or not 0 <= initial_attempts <= 2**31 - 1:
        raise ValueError("Invalid initial webhook attempt count")
    _reason(reason)
    created = _now(created_at) if created_at is not None else now
    digest = hashlib.sha256(payload).hexdigest()
    with get_session_maker()() as session, session.begin():
        queue = _queue(session, queue_id, now, create=True)
        if coalesce and not legacy:
            # This survives sent-row cleanup. A delayed Redis snapshot must
            # never replace a more recent native SQL snapshot, even after send.
            queue.native_snapshot_seen = True
        lookup = [WebhookOutboxDelivery.message_id == message_id]
        if dedupe_key is not None:
            lookup.append(WebhookOutboxDelivery.dedupe_key == dedupe_key)
        existing = session.scalar(select(WebhookOutboxDelivery).where(or_(*lookup)))
        if existing is None:
            state = initial_status
            admission_reason = reason
            if legacy and state == "queued" and queue.legacy_review:
                state, admission_reason = "review", "operator_reset"
            elif legacy and coalesce and queue.native_snapshot_seen and state == "queued":
                state, admission_reason = "superseded", "newer_snapshot"
            record = WebhookOutboxDelivery(message_id=message_id, dedupe_key=dedupe_key,
                queue_hash=queue.queue_hash, payload=None if state == "superseded" else payload,
                payload_sha256=digest,
                server_number=server_number, webhook_type=webhook_type, message_type=message_type,
                status=state, priority=0 if legacy else 1,
                source_acknowledged=not legacy, attempts=initial_attempts,
                reason=reason, available_at=now, created_at=created, updated_at=now,
                completed_at=created if state == "review" else now if state == "superseded" else None)
            record.reason = admission_reason
            try:
                with session.begin_nested():
                    session.add(record)
                    session.flush()
            except IntegrityError:
                existing = session.scalar(select(WebhookOutboxDelivery).where(or_(*lookup)))
                if existing is None:
                    raise
            else:
                if coalesce and state == "queued":
                    # Coalescing is explicitly opt-in for transient snapshots.
                    # In-flight HTTP requests and ordinary reports remain intact.
                    session.execute(update(WebhookOutboxDelivery).where(
                        WebhookOutboxDelivery.queue_hash == queue.queue_hash,
                        WebhookOutboxDelivery.id != record.id,
                        WebhookOutboxDelivery.status == "queued").values(
                            status="superseded", payload=None, completed_at=now,
                            updated_at=now, reason="newer_snapshot"))
                return message_id
        if existing.queue_hash != queue.queue_hash or existing.payload_sha256 != digest:
            raise ValueError("Outbox idempotency identifier was reused for different content")
        return existing.message_id


def _recover(session, now, *, queue_hash=None, limit=100):
    query = select(WebhookOutboxDelivery).where(WebhookOutboxDelivery.status.in_(("claimed", "sending")),
        WebhookOutboxDelivery.lease_until <= now)
    if queue_hash is not None:
        query = query.where(WebhookOutboxDelivery.queue_hash == queue_hash)
    rows = session.scalars(query.order_by(WebhookOutboxDelivery.id).limit(limit)
                           .with_for_update(skip_locked=True)).all()
    changed = 0
    for row in rows:
        sending = row.status == "sending"
        changed += session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.id == row.id, WebhookOutboxDelivery.status == row.status,
            WebhookOutboxDelivery.owner_token == row.owner_token,
            WebhookOutboxDelivery.lease_until <= now).values(
                status="review" if sending else "queued", owner_token=None, lease_until=None,
                reason="delivery_interrupted" if sending else "claim_expired", available_at=now,
                updated_at=now, completed_at=now if sending else None)
                .execution_options(synchronize_session="fetch")).rowcount
    return changed


@_safe_storage
def recover_expired(*, limit=100, now=None):
    with get_session_maker()() as session, session.begin():
        return _recover(session, _now(now), limit=_bound(limit))


@_safe_storage
def pending_queues(*, limit=100, now=None):
    """Bounded ready queue discovery, considering each queue's oldest active row."""
    now = _now(now)
    with get_session_maker()() as session, session.begin():
        _recover(session, now, limit=_bound(limit))
        heads = select(WebhookOutboxDelivery.id, func.row_number().over(
            partition_by=WebhookOutboxDelivery.queue_hash,
            order_by=(WebhookOutboxDelivery.priority, WebhookOutboxDelivery.id)).label("ordinal"))
        heads = heads.where(WebhookOutboxDelivery.status.in_(ACTIVE)).subquery()
        busy = select(WebhookOutboxDelivery.queue_hash).where(
            WebhookOutboxDelivery.status.in_(("claimed", "sending")))
        return list(session.scalars(select(WebhookOutboxQueue.queue_id)
            .join(WebhookOutboxDelivery, WebhookOutboxDelivery.queue_hash == WebhookOutboxQueue.queue_hash)
            .join(heads, heads.c.id == WebhookOutboxDelivery.id)
            .where(heads.c.ordinal == 1, WebhookOutboxDelivery.status == "queued",
                   WebhookOutboxDelivery.available_at <= now,
                   WebhookOutboxQueue.queue_hash.not_in(busy))
            .order_by(WebhookOutboxDelivery.id).limit(limit)))


@_safe_storage
def claim(queue_id, *, lease_seconds=120, now=None):
    now = _now(now)
    lease = timedelta(seconds=_seconds(lease_seconds))
    with get_session_maker()() as session, session.begin():
        queue = _queue(session, queue_id, now, skip_locked=True)
        if queue is None:
            return None
        _recover(session, now, queue_hash=queue.queue_hash, limit=1)
        in_flight = session.scalar(select(WebhookOutboxDelivery.id).where(
            WebhookOutboxDelivery.queue_hash == queue.queue_hash,
            WebhookOutboxDelivery.status.in_(("claimed", "sending"))).limit(1))
        if in_flight is not None:
            return None
        row = session.scalar(select(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.queue_hash == queue.queue_hash, WebhookOutboxDelivery.status.in_(ACTIVE))
            .order_by(WebhookOutboxDelivery.priority, WebhookOutboxDelivery.id).limit(1).with_for_update())
        if row is None or row.status != "queued":
            return None
        available = row.available_at.replace(tzinfo=timezone.utc) if row.available_at.tzinfo is None else row.available_at
        if available > now:
            return None
        token = uuid4().hex
        attempts = row.attempts
        changed = session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.id == row.id, WebhookOutboxDelivery.status == "queued",
            WebhookOutboxDelivery.available_at <= now).values(status="claimed", owner_token=token,
                lease_until=now + lease, attempts=attempts, updated_at=now)
                .execution_options(synchronize_session="fetch")).rowcount
        if changed != 1:
            return None
        return Claim(row.message_id, token, row.payload, queue_id, attempts, row.server_number,
                     bool(row.operator_retry))


@_safe_storage
def mark_sending(message_id, token, *, lease_seconds=120, now=None):
    now = _now(now)
    until = now + timedelta(seconds=_seconds(lease_seconds))
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.message_id == message_id, WebhookOutboxDelivery.owner_token == token,
            WebhookOutboxDelivery.status == "claimed", WebhookOutboxDelivery.lease_until > now)
            .values(status="sending", updated_at=now, lease_until=until,
                    attempts=case((WebhookOutboxDelivery.attempts < 2**31 - 1,
                                   WebhookOutboxDelivery.attempts + 1),
                                  else_=WebhookOutboxDelivery.attempts))).rowcount == 1


@_safe_storage
def renew(message_id, token, *, lease_seconds=120, now=None):
    now = _now(now)
    until = now + timedelta(seconds=_seconds(lease_seconds))
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.message_id == message_id, WebhookOutboxDelivery.owner_token == token,
            WebhookOutboxDelivery.status.in_(("claimed", "sending")), WebhookOutboxDelivery.lease_until > now)
            .values(lease_until=until, updated_at=now)).rowcount == 1


@_safe_storage
def finish(message_id, token, *, status, reason=None, retry_after_seconds=0, now=None):
    """Acknowledge HTTP before touching optional Redis rate-limit metadata."""
    now = _now(now)
    if status not in ("sent", "retry", "review"):
        raise ValueError("Invalid outbox completion")
    _reason(reason)
    if isinstance(retry_after_seconds, bool) or not isinstance(retry_after_seconds, (int, float)) or not math.isfinite(retry_after_seconds) or not 0 <= retry_after_seconds <= 86400:
        raise ValueError("Invalid webhook retry delay")
    values = dict(status="queued" if status == "retry" else status, reason=reason,
        available_at=now + timedelta(seconds=retry_after_seconds), owner_token=None, lease_until=None,
        updated_at=now, completed_at=None if status == "retry" else now)
    if status == "sent":
        values["payload"] = None
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.message_id == message_id, WebhookOutboxDelivery.owner_token == token,
            WebhookOutboxDelivery.status.in_(("sending",) if status == "sent" else ("claimed", "sending")))
            .values(**values)).rowcount == 1


@_safe_storage
def lookup(message_id):
    with get_session_maker()() as session:
        row = session.scalar(select(WebhookOutboxDelivery).where(WebhookOutboxDelivery.message_id == message_id))
        return _status(row) if row is not None else None


@_safe_storage
def list_review(*, limit=100, server_number=None):
    query = select(WebhookOutboxDelivery).where(WebhookOutboxDelivery.status == "review")
    if server_number is not None:
        query = query.where(WebhookOutboxDelivery.server_number == server_number)
    with get_session_maker()() as session:
        return [_status(row) for row in session.scalars(query.order_by(
            WebhookOutboxDelivery.updated_at.desc(), WebhookOutboxDelivery.id.desc()).limit(_bound(limit)))]


@_safe_storage
def retry_review(message_id, *, now=None):
    now = _now(now)
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.message_id == message_id, WebhookOutboxDelivery.status == "review",
            WebhookOutboxDelivery.payload.is_not(None)).values(status="queued", owner_token=None,
            lease_until=None, available_at=now, completed_at=None, updated_at=now,
            reason="operator_retry", attempts=0, operator_retry=True)).rowcount == 1


@_safe_storage
def acknowledge_source(message_id):
    """Record a confirmed legacy occurrence ACK after its Redis operation.

    Unacknowledged legacy tombstones never expire: a very late replay must
    still deduplicate even when Discord was already acknowledged long ago.
    """
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.message_id == message_id)
            .values(source_acknowledged=True)).rowcount == 1


@_safe_storage
def summary():
    with get_session_maker()() as session:
        return dict(session.execute(select(WebhookOutboxDelivery.status, func.count())
            .group_by(WebhookOutboxDelivery.status)).all())


@_safe_storage
def queue_lengths(*, limit=1000):
    """Bounded operator overview including leased, not-yet-acknowledged rows."""
    with get_session_maker()() as session:
        return dict(session.execute(select(WebhookOutboxQueue.queue_id, func.count())
            .join(WebhookOutboxDelivery, WebhookOutboxDelivery.queue_hash == WebhookOutboxQueue.queue_hash)
            .where(WebhookOutboxDelivery.status.in_(ACTIVE))
            .group_by(WebhookOutboxQueue.queue_id).order_by(WebhookOutboxQueue.queue_id)
            .limit(_bound(limit))).all())


@_safe_storage
def count_review():
    with get_session_maker()() as session:
        return int(session.scalar(select(func.count()).select_from(WebhookOutboxDelivery)
            .where(WebhookOutboxDelivery.status == "review")) or 0)


@_safe_storage
def review_queue(queue_id, *, reason="operator_reset", now=None):
    """Retain unsent messages on an explicit reset, fencing existing claims.

    A send already committed to HTTP cannot be safely cancelled by deleting its
    queue. Its owner still records the acknowledged or uncertain outcome.
    """
    now = _now(now)
    _reason(reason)
    with get_session_maker()() as session, session.begin():
        queue = _queue(session, queue_id, now, create=True)
        # Importers may drain only a bounded prefix during a reset. Persist
        # the decision so later legacy occurrences cannot escape that reset.
        queue.legacy_review = True
        queue.legacy_review_generation = uuid4().hex
        return session.execute(update(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.queue_hash == queue.queue_hash,
            WebhookOutboxDelivery.status.in_(("queued", "claimed"))).values(
                status="review", owner_token=None, lease_until=None,
                reason=reason, updated_at=now, completed_at=now)).rowcount


@_safe_storage
def get_legacy_review_generation(queue_id):
    """Capture the reset generation before checking the legacy Redis source."""
    key = _queue_hash(queue_id)
    with get_session_maker()() as session:
        return session.scalar(select(WebhookOutboxQueue.legacy_review_generation).where(
            WebhookOutboxQueue.queue_hash == key, WebhookOutboxQueue.legacy_review.is_(True)))


@_safe_storage
def clear_legacy_review(queue_id, *, expected_generation=None):
    """Clear only the generation whose Redis source was proven drained.

    A newer reset may happen between that Redis check and this SQL update.
    Its barrier must survive an older importer's delayed cleanup.
    """
    key = _queue_hash(queue_id)
    if not isinstance(expected_generation, str) or not re.fullmatch(r"[0-9a-f]{32}", expected_generation):
        return False
    with get_session_maker()() as session, session.begin():
        return session.execute(update(WebhookOutboxQueue).where(
            WebhookOutboxQueue.queue_hash == key, WebhookOutboxQueue.legacy_review.is_(True),
            WebhookOutboxQueue.legacy_review_generation == expected_generation).values(
                legacy_review=False, legacy_review_generation=None)).rowcount == 1


@_safe_storage
def cleanup_sent(*, retention_days=30, limit=100, now=None):
    """Only acknowledged or explicitly coalesced, scrubbed tombstones expire."""
    if isinstance(retention_days, bool) or not isinstance(retention_days, int) or retention_days < 1:
        raise ValueError("Invalid sent webhook retention")
    cutoff = _now(now) - timedelta(days=retention_days)
    with get_session_maker()() as session, session.begin():
        ids = list(session.scalars(select(WebhookOutboxDelivery.id).where(
            WebhookOutboxDelivery.status.in_(("sent", "superseded")), WebhookOutboxDelivery.payload.is_(None),
            WebhookOutboxDelivery.source_acknowledged.is_(True),
            WebhookOutboxDelivery.completed_at < cutoff).order_by(WebhookOutboxDelivery.id)
            .limit(_bound(limit)).with_for_update(skip_locked=True)))
        if not ids:
            return 0
        return session.execute(delete(WebhookOutboxDelivery).where(
            WebhookOutboxDelivery.id.in_(ids), WebhookOutboxDelivery.status.in_(("sent", "superseded")),
            WebhookOutboxDelivery.payload.is_(None), WebhookOutboxDelivery.source_acknowledged.is_(True))).rowcount
