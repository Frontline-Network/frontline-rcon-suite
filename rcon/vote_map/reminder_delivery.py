"""Durable, per-recipient reservation for one map-vote reminder batch.

The caller must provide a stable batch ID for retries of the same reminder.
Only a confirmed rejection may be retried; unknown results remain reserved.
"""
import time
import uuid
import hashlib
from collections import Counter

from sqlalchemy import CheckConstraint, Column, Float, Integer, MetaData, String, Table, Text, UniqueConstraint, and_, func, or_, select, text, update
from rcon.models import get_session_maker

metadata = MetaData()
reminder_clock = Table(
    "votemap_reminder_clock", metadata,
    Column("server_number", Integer, primary_key=True),
    Column("completed_at", Float, nullable=False),
    Column("outcome", String(16), nullable=False),
    CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_clock_server"),
    CheckConstraint("outcome IN ('success', 'partial', 'failed')", name="ck_votemap_clock_outcome"),
)
reminder_batch = Table(
    "votemap_reminder_batch", metadata,
    Column("server_number", Integer, primary_key=True),
    Column("scope", String(100), primary_key=True),
    Column("batch_id", String(64), nullable=False),
    Column("signature", String(64), nullable=False),
    Column("message", Text, nullable=False),
    Column("status", String(16), nullable=False),
    Column("created_at", Float, nullable=False),
    Column("completed_at", Float, nullable=True),
    UniqueConstraint("server_number", "batch_id", name="uq_votemap_batch_server_id"),
    CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_batch_server"),
    CheckConstraint("status IN ('open', 'completed')", name="ck_votemap_batch_status"),
)
reminder_delivery = Table(
    "votemap_reminder_delivery", metadata,
    Column("server_number", Integer, primary_key=True),
    Column("batch_id", String(64), primary_key=True),
    Column("player_id", String(100), primary_key=True),
    Column("token", String(32), nullable=False),
    Column("status", String(16), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("updated_at", Float, nullable=False),
    Column("retry_at", Float, nullable=False),
    CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_notice_server"),
    CheckConstraint("status IN ('queued', 'sending', 'sent', 'rejected', 'unknown', 'skipped')", name="ck_votemap_notice_status"),
    CheckConstraint("attempts >= 0", name="ck_votemap_notice_attempts"),
)

RETRY_DELAY_SECONDS = 30
MAX_ATTEMPTS = 3
UNCERTAIN_AFTER_SECONDS = 300
FAILED_RETRY_SECONDS = 300


def _lock_server(session, server_number):
    if session.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(hashlib.sha256(f"votemap-reminder:{server_number}".encode()).digest()[:8], "big", signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def open_batch(server_number, scope, signature, message, player_ids, *, now=None, min_interval=0, force=False, once=False, is_current=None):
    """Atomically snapshot all recipients, or resume the matching open batch."""
    if not (1 <= server_number <= 32 and 1 <= len(scope) <= 100 and 1 <= len(signature) <= 64 and min_interval >= 0):
        raise ValueError("Invalid reminder batch identity")
    players = sorted(set(player_ids))
    if any(not isinstance(pid, str) or not 1 <= len(pid) <= 100 for pid in players):
        raise ValueError("Invalid reminder recipient")
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        _lock_server(session, server_number)
        if is_current is not None and not is_current():
            return None
        where = and_(reminder_batch.c.server_number == server_number, reminder_batch.c.scope == scope)
        current = session.execute(select(reminder_batch).where(where).with_for_update()).mappings().one_or_none()
        if current and current["status"] == "open" and current["signature"] == signature:
            return current["batch_id"]
        if current and current["status"] == "completed" and once and current["signature"] == signature:
            return None
        if not force:
            clock = session.execute(select(reminder_clock).where(
                reminder_clock.c.server_number == server_number)).mappings().one_or_none()
            if clock:
                interval = min(min_interval, FAILED_RETRY_SECONDS) if clock["outcome"] == "failed" else min_interval
                if now - clock["completed_at"] < interval:
                    return None
        batch_id = uuid.uuid4().hex
        values = dict(batch_id=batch_id, signature=signature, message=message,
                      status="open", created_at=now, completed_at=None)
        if current:
            if current["status"] == "open":
                old = and_(reminder_delivery.c.server_number == server_number,
                           reminder_delivery.c.batch_id == current["batch_id"])
                session.execute(update(reminder_delivery).where(
                    old, reminder_delivery.c.status.in_(["queued", "rejected"])
                ).values(status="skipped", updated_at=now))
                session.execute(update(reminder_delivery).where(
                    old, reminder_delivery.c.status == "sending"
                ).values(status="unknown", updated_at=now))
            session.execute(update(reminder_batch).where(where).values(**values))
        else:
            session.execute(reminder_batch.insert().values(server_number=server_number, scope=scope, **values))
        if players:
            session.execute(reminder_delivery.insert(), [dict(
                server_number=server_number, batch_id=batch_id, player_id=pid,
                token="", status="queued", attempts=0, updated_at=now, retry_at=now,
            ) for pid in players])
        return batch_id


def reserve(server_number, batch_id, player_id, *, now=None):
    """Commit a reservation before a network action; return its token or None."""
    if not (1 <= server_number <= 32 and 1 <= len(batch_id) <= 64 and 1 <= len(player_id) <= 100):
        raise ValueError("Invalid reminder delivery identity")
    now = time.time() if now is None else now
    token = uuid.uuid4().hex
    with get_session_maker()() as session, session.begin():
        active = session.execute(select(reminder_batch.c.batch_id).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
            reminder_batch.c.status == "open",
        ).with_for_update()).scalar_one_or_none()
        if active is None:
            return None
        active_batch = select(reminder_batch.c.batch_id).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
            reminder_batch.c.status == "open",
        ).exists()
        statement = update(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            reminder_delivery.c.player_id == player_id,
            active_batch,
            or_(reminder_delivery.c.status == "queued",
                and_(reminder_delivery.c.status == "rejected", reminder_delivery.c.retry_at <= now,
                     reminder_delivery.c.attempts < MAX_ATTEMPTS)),
        ).values(token=token, status="sending", attempts=reminder_delivery.c.attempts + 1,
                 updated_at=now, retry_at=now).returning(reminder_delivery.c.token)
        return session.execute(statement).scalar_one_or_none()


def finish(server_number, batch_id, player_id, token, outcome, *, now=None):
    """Finalize only the current reservation; late responses cannot overwrite it."""
    if outcome not in {"sent", "rejected", "unknown", "skipped"} or not token:
        raise ValueError("Invalid reminder delivery result")
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        result = session.execute(
            update(reminder_delivery).where(
                reminder_delivery.c.server_number == server_number,
                reminder_delivery.c.batch_id == batch_id,
                reminder_delivery.c.player_id == player_id,
                reminder_delivery.c.token == token,
                reminder_delivery.c.status == "sending",
            ).values(status=outcome, updated_at=now,
                     retry_at=now + RETRY_DELAY_SECONDS if outcome == "rejected" else now)
        )
        return result.rowcount == 1


def batch_state(server_number, batch_id):
    """Return the persisted message and full recipient snapshot for a batch."""
    with get_session_maker()() as session:
        batch = session.execute(select(reminder_batch).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
        )).mappings().one_or_none()
        if not batch:
            return None
        recipients = session.execute(select(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
        )).mappings().all()
        return {"batch": dict(batch), "recipients": [dict(row) for row in recipients]}


def open_batches(server_number):
    """List outstanding batches so scheduled workers can resume event sends."""
    with get_session_maker()() as session:
        rows = session.execute(select(reminder_batch).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.status == "open",
        ).order_by(reminder_batch.c.created_at)).mappings().all()
        return [dict(row) for row in rows]


def abandon_batch(server_number, batch_id, *, now=None, is_current=None):
    """Retire an outdated round without releasing uncertain reservations."""
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        _lock_server(session, server_number)
        if is_current is not None and not is_current():
            return False
        current = session.execute(select(reminder_batch.c.batch_id).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
            reminder_batch.c.status == "open",
        ).with_for_update()).scalar_one_or_none()
        if current is None:
            return False
        session.execute(update(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            reminder_delivery.c.status.in_(["queued", "rejected"]),
        ).values(status="skipped", updated_at=now))
        session.execute(update(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            reminder_delivery.c.status == "sending",
        ).values(status="unknown", updated_at=now))
        session.execute(update(reminder_batch).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
        ).values(status="completed", completed_at=now))
        return True


def skip(server_number, batch_id, player_id, *, now=None):
    """Skip a no-longer-eligible recipient without changing an in-flight result."""
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        result = session.execute(update(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            reminder_delivery.c.player_id == player_id,
            reminder_delivery.c.status.in_(["queued", "rejected"]),
        ).values(status="skipped", updated_at=now))
        return result.rowcount == 1


def recover_uncertain(server_number, batch_id, *, now=None):
    """After a generous timeout, retain abandoned sends as unknown, never retry."""
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        current = session.execute(select(reminder_batch.c.batch_id).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
            reminder_batch.c.status == "open",
        ).with_for_update()).scalar_one_or_none()
        if current is None:
            return 0
        result = session.execute(update(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            reminder_delivery.c.status == "sending",
            reminder_delivery.c.updated_at <= now - UNCERTAIN_AFTER_SECONDS,
        ).values(status="unknown", updated_at=now))
        return result.rowcount


def complete_batch(server_number, batch_id, *, now=None):
    """Complete only after every snapshotted recipient has a terminal outcome."""
    now = time.time() if now is None else now
    with get_session_maker()() as session, session.begin():
        _lock_server(session, server_number)
        current = session.execute(select(reminder_batch).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
            reminder_batch.c.status == "open",
        ).with_for_update()).mappings().one_or_none()
        if not current:
            return False
        unfinished = session.execute(select(func.count()).select_from(reminder_delivery).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
            or_(reminder_delivery.c.status.in_(["queued", "sending"]),
                and_(reminder_delivery.c.status == "rejected", reminder_delivery.c.attempts < MAX_ATTEMPTS)),
        )).scalar_one()
        if unfinished:
            return False
        statuses = session.execute(select(reminder_delivery.c.status, func.count()).where(
            reminder_delivery.c.server_number == server_number,
            reminder_delivery.c.batch_id == batch_id,
        ).group_by(reminder_delivery.c.status)).all()
        counts = dict(statuses)
        failed = counts.get("rejected", 0)
        uncertain = counts.get("unknown", 0)
        successful = counts.get("sent", 0)
        outcome = "partial" if uncertain or (failed and successful) else "failed" if failed else "success"
        session.execute(update(reminder_batch).where(
            reminder_batch.c.server_number == server_number,
            reminder_batch.c.batch_id == batch_id,
        ).values(status="completed", completed_at=now))
        clock_where = reminder_clock.c.server_number == server_number
        if session.execute(select(reminder_clock.c.server_number).where(clock_where)).scalar_one_or_none() is None:
            session.execute(reminder_clock.insert().values(server_number=server_number, completed_at=now, outcome=outcome))
        else:
            session.execute(update(reminder_clock).where(clock_where).values(completed_at=now, outcome=outcome))
        return True


def dispatch(server_number, batch_id, eligible_ids, send, is_current, *, now=None):
    """Deliver a snapshotted batch without replaying completed/uncertain sends.

    ``send`` is invoked only after its reservation commits; callers must disable
    transport retries and provide a fresh round check in ``is_current``.
    """
    clock = time.time if now is None else lambda: now
    recover_uncertain(server_number, batch_id, now=clock())
    state = batch_state(server_number, batch_id)
    if not state:
        return {"complete": False, "stale": True, "counts": {}}
    if state["batch"]["status"] == "completed":
        return {"complete": True, "stale": False,
                "counts": dict(Counter(row["status"] for row in state["recipients"]))}
    eligible = set(eligible_ids)
    for row in state["recipients"]:
        pid = row["player_id"]
        if not is_current():
            return {"complete": False, "stale": True, "counts": {}}
        if pid not in eligible:
            skip(server_number, batch_id, pid, now=clock())
            continue
        token = reserve(server_number, batch_id, pid, now=clock())
        if not token:
            continue
        if not is_current():
            finish(server_number, batch_id, pid, token, "skipped", now=clock())
            return {"complete": False, "stale": True, "counts": {}}
        try:
            response = send(pid, state["batch"]["message"])
            outcome = "sent" if response is True else "rejected" if response is False else "unknown"
        except Exception:
            outcome = "unknown"
        finish(server_number, batch_id, pid, token, outcome, now=clock())
    completed = complete_batch(server_number, batch_id, now=clock())
    updated = batch_state(server_number, batch_id)
    counts = dict(Counter(row["status"] for row in updated["recipients"])) if updated else {}
    completed = completed or bool(updated and updated["batch"]["status"] == "completed")
    return {"complete": completed, "stale": not bool(updated), "counts": counts}
