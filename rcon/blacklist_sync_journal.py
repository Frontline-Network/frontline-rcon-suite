"""Durable per-server delivery for blacklist changes.

Producers enqueue in the same transaction as the blacklist mutation. The
worker persists an in-flight marker before calling the game server: after a
crash or ambiguous reply that marker must be reviewed, never replayed blindly.
"""

from datetime import datetime, timezone
import hashlib
import logging
from time import monotonic

from sqlalchemy import TIMESTAMP, CheckConstraint, LargeBinary, String, Text, func, select, text
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base, get_session_maker
from rcon.vip_rewards.locking import lock

logger = logging.getLogger(__name__)


class BlacklistSyncDelivery(Base):
    __tablename__ = "blacklist_sync_delivery"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    command: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_blacklist_sync_server"),
        CheckConstraint("status IN ('queued', 'sending', 'done', 'review', 'reviewed')", name="ck_blacklist_sync_status"),
    )


def _lock_targets(session, targets: list[int]) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 0x464C4E424C53594E})
    for number in targets:
        key = int.from_bytes(hashlib.sha256(f"blacklist-sync:{number}".encode()).digest()[:8], "big", signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def enqueue(session, command: bytes, server_mask: int) -> int:
    """Stage one delivery per target; caller commits it with the mutation.

    The transaction-scoped lock makes serial ID order match commit order. A
    server can therefore process its own deliveries in order even when
    multiple API workers edit the blacklist concurrently.
    """
    if not 0 <= server_mask <= 0xFFFFFFFF:
        raise ValueError("Server mask must be an unsigned 32-bit integer")
    targets = [number for number in range(1, 33) if server_mask & (1 << (number - 1))]
    if not targets:
        return 0
    # A worker holds the matching session lock while it reads the latest
    # blacklist state and performs RCON work. A producer cannot commit a new
    # state for a target midway through that operation.
    _lock_targets(session, targets)
    now = datetime.now(timezone.utc)
    session.add_all([
        BlacklistSyncDelivery(server_number=number, command=command, status="queued",
                              created_at=now, updated_at=now)
        for number in targets
    ])
    return len(targets)


def enqueue_connect_reconciliation(server_number: int, player_id: str, record_id: int,
                                   started_at: datetime) -> bool:
    """Persist one retry after an unattempted connect-time identity check.

    A matching pending/review item or a completion since this connect started
    already covers the work. This enqueues an intent only; it does not mutate
    blacklist state. The producer lock serializes it with other enqueues, but
    taking the target lock here would block all producers while a worker is
    waiting for the game server. Workers publish their sending state before
    acting, so the read below can also deduplicate against in-flight work.
    """
    from rcon.blacklist import BlacklistCommand, BlacklistCommandType

    if not 1 <= server_number <= 32 or not player_id or record_id <= 0 or started_at.tzinfo is None:
        raise ValueError('Invalid connect reconciliation')
    mask = 1 << (server_number - 1)
    with get_session_maker()() as session, session.begin():
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 0x464C4E424C53594E})
        rows = session.execute(select(BlacklistSyncDelivery.command, BlacklistSyncDelivery.status)
            .where(BlacklistSyncDelivery.server_number == server_number,
                   ((BlacklistSyncDelivery.status.in_(('queued', 'sending', 'review'))) |
                    ((BlacklistSyncDelivery.status == 'done') &
                     (BlacklistSyncDelivery.updated_at >= started_at))))).all()
        overlap = False
        for row in rows:
            try:
                existing = BlacklistCommand.decode(row.command)
                if (existing.command == BlacklistCommandType.CREATE_RECORD
                        and existing.payload.get('record_id') == record_id
                        and existing.payload.get('player_id') == player_id):
                    return False
                if existing.command == BlacklistCommandType.CREATE_RECORD:
                    overlap |= existing.payload.get('player_id') == player_id
                elif existing.command in (BlacklistCommandType.EDIT_RECORD, BlacklistCommandType.DELETE_RECORD):
                    overlap |= existing.payload['old_record']['player_id'] == player_id
                elif existing.command == BlacklistCommandType.EXPIRE_ALL:
                    overlap |= existing.payload['player_id'] == player_id
                elif existing.command in (BlacklistCommandType.EDIT_LIST, BlacklistCommandType.DELETE_LIST):
                    # A list change may include this player. The worker may
                    # already have passed its overlap check before this new
                    # intent was enqueued, so do not replay it automatically.
                    overlap = True
            except Exception:
                overlap = True
        command = BlacklistCommand(command=BlacklistCommandType.CREATE_RECORD, server_mask=mask,
                                   payload={'player_id': player_id, 'record_id': record_id})
        now = datetime.now(timezone.utc)
        session.add(BlacklistSyncDelivery(server_number=server_number, command=command.encode(),
                                          status='review' if overlap else 'queued',
                                          reason='overlapping blacklist changes require reconciliation before connect action' if overlap else None,
                                          created_at=now, updated_at=now))
        return True


def process_one(server_number: int, handler, *, is_ready=None, prepare=None) -> str:
    """Process the oldest server delivery, failing closed on ambiguous work."""
    if not 1 <= server_number <= 32:
        raise ValueError("Server number must be between 1 and 32")
    maker = get_session_maker()
    ready = is_ready is None
    probed_at = None
    prepared_at = prepared_id = prepared = None
    if is_ready is not None or prepare is not None:
        # A probe can block for the full RCON timeout. Never hold the shared
        # producer/worker lock while waiting for an offline server: that would
        # also stall unrelated blacklist writes and their API responses.
        with maker() as session:
            first = session.execute(
                select(BlacklistSyncDelivery.id, BlacklistSyncDelivery.status,
                       BlacklistSyncDelivery.command)
                .where(BlacklistSyncDelivery.server_number == server_number,
                       BlacklistSyncDelivery.status.in_(("queued", "sending", "review")))
                .order_by(BlacklistSyncDelivery.id).limit(1)
            ).one_or_none()
        if first is None:
            return "empty"
        if first.status == "queued":
            if is_ready is not None:
                try:
                    ready = is_ready() is True
                    probed_at = monotonic()
                except Exception:
                    ready = False
            if ready and prepare is not None:
                try:
                    prepared = prepare(first.command)
                    prepared_id = first.id
                    prepared_at = monotonic()
                except Exception as exc:
                    # No side effect was attempted. Leave the row queued for
                    # a later fresh read rather than marking it uncertain.
                    logger.warning('Blacklist preparation deferred (%s)', type(exc).__name__)
                    return "deferred"

    with lock(f"blacklist-sync:{server_number}"):
        with maker() as session, session.begin():
            row = session.scalar(
                select(BlacklistSyncDelivery)
                .where(BlacklistSyncDelivery.server_number == server_number,
                       BlacklistSyncDelivery.status.in_(("queued", "sending", "review")))
                .order_by(BlacklistSyncDelivery.id)
                .limit(1).with_for_update()
            )
            if row is None:
                return "empty"
            if row.status == "review":
                return "review"
            if row.status == "sending":
                row.status = "review"
                row.reason = "process ended before delivery was confirmed"
                row.updated_at = datetime.now(timezone.utc)
                return "review"
            if not ready or (probed_at is not None and monotonic() - probed_at > 5):
                # The oldest row may have changed during the unlocked probe.
                # A queued action needs a successful probe before dispatch.
                return "deferred"
            if prepare is not None and (prepared_id != row.id or prepared_at is None
                                        or monotonic() - prepared_at > 5):
                # Another worker may have advanced the queue while preparing.
                # Never apply a snapshot to a different or stale delivery.
                return "deferred"
            # The handlers read the current source state. Consecutive changes
            # to the same record therefore need one reconciliation, not one
            # RCON action per historical version.
            from rcon.blacklist import BlacklistCommand, BlacklistCommandType
            following = session.scalars(
                select(BlacklistSyncDelivery)
                .where(BlacklistSyncDelivery.server_number == server_number,
                       BlacklistSyncDelivery.id > row.id,
                       BlacklistSyncDelivery.status.in_(("queued", "sending", "review")))
                .order_by(BlacklistSyncDelivery.id).with_for_update()
            ).all()
            group = [row]
            before = None
            try:
                before = BlacklistCommand.decode(row.command)
                if before.command == BlacklistCommandType.CREATE_RECORD:
                    record_id = before.payload["record_id"]
                    player_id = before.payload["player_id"]
                elif before.command == BlacklistCommandType.EDIT_RECORD:
                    record_id = before.payload["old_record"]["id"]
                    player_id = before.payload["old_record"]["player_id"]
                else:
                    record_id, player_id = None, None
            except Exception:
                record_id, player_id = None, None
            def identity(command):
                if command.command in (BlacklistCommandType.CREATE_RECORD, BlacklistCommandType.EXPIRE_ALL):
                    return command.payload["player_id"]
                if command.command in (BlacklistCommandType.EDIT_RECORD, BlacklistCommandType.DELETE_RECORD):
                    return command.payload["old_record"]["player_id"]
                return None

            # A list-wide change or changes to different records for the same
            # player can invalidate the old-state assumptions of queued
            # handlers. Fail closed until an operator reconciles the affected
            # game-server state; never replay a potentially stale removal.
            ambiguous_all = record_id is None and before is not None and bool(following)
            ambiguous_player = False
            affected = []
            for item in following:
                if before is None:
                    break
                try:
                    candidate = BlacklistCommand.decode(item.command)
                    candidate_player = identity(candidate)
                    if candidate_player is None:
                        ambiguous_all = True
                    elif candidate_player == player_id:
                        affected.append(item)
                        candidate_record = (candidate.payload.get("record_id") if candidate.command == BlacklistCommandType.CREATE_RECORD
                                            else candidate.payload.get("old_record", {}).get("id"))
                        if candidate_record != record_id:
                            ambiguous_player = True
                except Exception:
                    ambiguous_all = True
            if ambiguous_all or ambiguous_player:
                for item in ([row] + (list(following) if ambiguous_all else affected)):
                    if item.status in ("queued", "sending"):
                        item.status = "review"
                        item.reason = "overlapping offline blacklist changes require reconciliation"
                        item.updated_at = datetime.now(timezone.utc)
                return "review"
            last_command = before
            for item in following:
                if record_id is None or item.status != "queued":
                    break
                try:
                    next_command = BlacklistCommand.decode(item.command)
                    same_record = (next_command.command in (BlacklistCommandType.EDIT_RECORD, BlacklistCommandType.DELETE_RECORD) and
                                   next_command.payload["old_record"]["id"] == record_id)
                    if next_command.command == BlacklistCommandType.CREATE_RECORD:
                        next_player = next_command.payload["player_id"]
                    elif next_command.command in (BlacklistCommandType.EDIT_RECORD, BlacklistCommandType.DELETE_RECORD):
                        next_player = next_command.payload["old_record"]["player_id"]
                    elif next_command.command == BlacklistCommandType.EXPIRE_ALL:
                        next_player = next_command.payload["player_id"]
                    else:
                        next_player = None
                except Exception:
                    break
                if not same_record:
                    # Events for different players commute. A list-wide or
                    # same-player change remains an ordering barrier.
                    if next_player is not None and next_player != player_id:
                        continue
                    break
                group.append(item)
                last_command = next_command
                if next_command.command == BlacklistCommandType.DELETE_RECORD:
                    break
            now = datetime.now(timezone.utc)
            if (len(group) > 1 and before.command == BlacklistCommandType.CREATE_RECORD and
                    last_command.command == BlacklistCommandType.DELETE_RECORD):
                for item in group:
                    item.status, item.reason, item.updated_at = "done", "unapplied creation cancelled by deletion", now
                return "done"
            for item in group:
                item.status, item.updated_at = "sending", now
            delivery_ids, command = [item.id for item in group], row.command

        try:
            if (handler(command, prepared) if prepare is not None else handler(command)) is False:
                raise RuntimeError("game server rejected blacklist synchronization")
        except Exception as exc:
            with maker() as session, session.begin():
                rows = session.scalars(select(BlacklistSyncDelivery).where(BlacklistSyncDelivery.id.in_(delivery_ids)).with_for_update()).all()
                for item in rows:
                    item.status = "review"
                    item.reason = f"unconfirmed: {type(exc).__name__}"
                    item.updated_at = datetime.now(timezone.utc)
            return "review"
        with maker() as session, session.begin():
            rows = session.scalars(select(BlacklistSyncDelivery).where(BlacklistSyncDelivery.id.in_(delivery_ids)).with_for_update()).all()
            for item in rows:
                item.status = "done"
                item.updated_at = datetime.now(timezone.utc)
        return "done"


def acknowledge_review(server_number: int, delivery_id: int, actor: str) -> bool:
    """Record an operator's manual review without performing a game action."""
    if not actor or not actor.strip():
        raise ValueError("A reviewing operator is required")
    if not 1 <= server_number <= 32:
        raise ValueError("Server number must be between 1 and 32")
    with lock(f"blacklist-sync:{server_number}"):
        maker = get_session_maker()
        with maker() as session, session.begin():
            row = session.get(BlacklistSyncDelivery, delivery_id, with_for_update=True)
            if row is None or row.server_number != server_number or row.status != "review":
                return False
            row.status = "reviewed"
            row.reason = f"{row.reason or 'unconfirmed'}; reviewed by {actor.strip()}"
            row.updated_at = datetime.now(timezone.utc)
            return True


def list_reviews(server_number: int, offset: int = 0, limit: int = 50) -> dict:
    """Return only this server's unconfirmed work for authorized operators."""
    from rcon.blacklist import BlacklistCommand

    server_number, offset, limit = int(server_number), int(offset), int(limit)
    if not 1 <= server_number <= 32 or offset < 0 or not 1 <= limit <= 100:
        raise ValueError("Invalid server or pagination")
    with get_session_maker()() as session:
        condition = (BlacklistSyncDelivery.server_number == server_number,
                     BlacklistSyncDelivery.status == "review")
        total = session.scalar(select(func.count()).select_from(BlacklistSyncDelivery).where(*condition))
        rows = session.scalars(select(BlacklistSyncDelivery).where(*condition)
                               .order_by(BlacklistSyncDelivery.id).offset(offset).limit(limit)).all()
        result = []
        for row in rows:
            try:
                command = BlacklistCommand.decode(row.command)
                command_name, payload = command.command.name, command.payload
            except Exception:
                command_name, payload = "INVALID", {}
            review_kind = {
                "unconfirmed: HLLVSteamBanOwnershipUnverified": "hllv_ownership",
                "unconfirmed: HLLVBanOwnershipUnverified": "hllv_ownership",
                "unconfirmed: HLLVSteamIdentityUnverified": "hllv_identity",
            }.get(row.reason)
            result.append({"id": row.id, "command": command_name, "payload": payload,
                           "review_kind": review_kind,
                           "reason": row.reason, "updated_at": row.updated_at.isoformat()})
        return {"total": total, "results": result}
