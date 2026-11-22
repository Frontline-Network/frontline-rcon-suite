"""Durable seed-cycle observations and per-player reward reservations.

This module never issues game-server commands. A completed observation and all
its grant records are committed together, so a worker restart can resume them.
"""

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from rcon.models import SeedVipCycle, SeedVipGrant, VipRewardGrant, get_session_maker
from rcon.vip_rewards.locking import vip_lock
from rcon.vip_rewards.service import current_vip, expiration, permanent, vip_for_reward


@dataclass(frozen=True)
class Observation:
    completed: bool
    generation: int
    phase: str
    seeded_at: datetime | None
    recipients: frozenset[str]


def observe(
    *,
    server_number: int,
    preview: bool,
    seeded: bool,
    player_count: int,
    eligible: dict[str, str],
    online_when_seeded: bool,
    buffer: timedelta,
    reward_seconds: float,
    cumulative: bool,
    reward_name: Callable[[str], str],
    now: datetime,
) -> Observation:
    """Record a poll and atomically enqueue one grant per eligible player.

    The row lock prevents two workers from completing the same cycle twice.
    """
    if now.tzinfo is None:
        raise ValueError("seed observation time must include a timezone")
    if reward_seconds < 0:
        raise ValueError("negative seed reward")
    if not all(isinstance(pid, str) and pid and isinstance(name, str)
               for pid, name in eligible.items()):
        raise ValueError("invalid seed reward recipient")

    # The general enter_session helper suppresses some database errors; the
    # seed transition must fail closed if its journal cannot commit.
    with get_session_maker()() as session, session.begin():
        session.execute(
            insert(SeedVipCycle)
            .values(server_number=server_number, preview=preview, generation=0,
                    phase="uninitialized", eligible={}, seeded_at=None, updated_at=now)
            .on_conflict_do_nothing(index_elements=["server_number", "preview"])
        )
        cycle = session.execute(
            select(SeedVipCycle)
            .where(SeedVipCycle.server_number == server_number, SeedVipCycle.preview == preview)
            .with_for_update()
        ).scalar_one()
        if cycle.phase == "uninitialized":
            cycle.phase = "seeded" if seeded else "seeding"
            if not seeded:
                cycle.generation += 1
        elif cycle.phase == "seeded" and not seeded and player_count > 0:
            if cycle.seeded_at is None or now - expiration(cycle.seeded_at) > buffer:
                cycle.phase = "seeding"
                cycle.generation += 1
                cycle.eligible = {}

        completed = False
        recipients = frozenset()
        if cycle.phase == "seeding":
            collected = {} if online_when_seeded else dict(cycle.eligible)
            collected.update(eligible)
            cycle.eligible = collected
            if seeded:
                recipients = frozenset(collected)
                for player_id, name in collected.items():
                    session.execute(
                        insert(SeedVipGrant)
                        .values(server_number=server_number, preview=preview,
                                generation=cycle.generation, player_id=player_id,
                                player_name=reward_name(name), status="preview" if preview else "queued",
                                reward_seconds=reward_seconds, cumulative=cumulative,
                                reward_time=now, updated_at=now)
                        .on_conflict_do_nothing(constraint="uq_seed_vip_grant_cycle_player")
                    )
                cycle.phase = "seeded"
                cycle.seeded_at = now
                cycle.eligible = {}
                completed = True
        cycle.updated_at = now
        return Observation(completed, cycle.generation, cycle.phase, cycle.seeded_at, recipients)


def pending(server_number: int) -> list[int]:
    """Return recoverable live grants in creation order."""
    with get_session_maker()() as session:
        return list(session.scalars(
            select(SeedVipGrant.id)
            .where(SeedVipGrant.server_number == server_number,
                   SeedVipGrant.preview.is_(False),
                   SeedVipGrant.status.in_(["queued", "prepared"]))
            .order_by(SeedVipGrant.id)
        ))


def grant_info(server_number: int, grant_id: int) -> tuple[str, datetime, str | None]:
    with get_session_maker()() as session:
        grant = session.get(SeedVipGrant, grant_id)
        if grant is None or grant.server_number != server_number or grant.target is None:
            raise ValueError("seed grant not found or lacks a target")
        return grant.player_id, grant.target, grant.reason


def list_grants(server_number: int, offset=0, limit=50, status=None) -> dict:
    """Expose a bounded, server-scoped history for operator review."""
    offset, limit = max(0, int(offset)), min(100, max(1, int(limit)))
    if status not in (None, "review"):
        raise ValueError("unsupported seed grant status filter")
    with get_session_maker()() as session:
        scope = [SeedVipGrant.server_number == server_number]
        if status:
            scope.append(SeedVipGrant.status == status)
        total = session.scalar(select(func.count()).select_from(SeedVipGrant).where(*scope))
        rows = session.scalars(
            select(SeedVipGrant).where(*scope).order_by(SeedVipGrant.id.desc())
            .offset(offset).limit(limit)
        )
        return {"total": total, "offset": offset, "results": [
            {"id": row.id, "player_id": row.player_id, "player_name": row.player_name,
             "generation": row.generation, "preview": row.preview, "status": row.status,
             "reward_seconds": row.reward_seconds, "target": row.target,
             "reason": row.reason, "updated_at": row.updated_at}
            for row in rows
        ]}


def acknowledge_review(server_number: int, grant_id: int, by: str) -> bool:
    """Record manual review; never repeat or modify the server-side grant."""
    from rcon.utils import get_server_number

    if int(get_server_number()) != server_number:
        return False
    maker = get_session_maker()
    with maker() as session:
        grant = session.get(SeedVipGrant, int(grant_id))
        if grant is None or grant.server_number != server_number:
            return False
        player_id = grant.player_id
    with vip_lock(player_id):
        with maker() as session, session.begin():
            grant = session.get(SeedVipGrant, int(grant_id), with_for_update=True)
            if grant is None or grant.server_number != server_number or grant.status != "review":
                return False
            grant.status = "reviewed"
            grant.reason = f"{grant.reason or 'uncertain_write'}; reviewed by {by}"
            grant.updated_at = datetime.now(timezone.utc)
            return True


def deliver(rcon, *, server_number: int, grant_id: int) -> str:
    """Attempt or reconcile one journaled grant without replaying writes.

    The caller must select grants for the active RCON server. A target is
    committed before the RCON call; after an interrupted call only readback is
    allowed, and a mismatch requires operator review.
    """
    from rcon.utils import get_server_number

    if int(get_server_number()) != server_number:
        raise ValueError("seed grant belongs to another server")
    maker = get_session_maker()
    with maker() as session:
        grant = session.get(SeedVipGrant, grant_id)
        if grant is None or grant.server_number != server_number:
            raise ValueError("seed grant not found for server")
        player_id = grant.player_id

    with vip_lock(player_id):
        with maker() as session, session.begin():
            grant = session.execute(
                select(SeedVipGrant).where(SeedVipGrant.id == grant_id).with_for_update()
            ).scalar_one()
            if grant.server_number != server_number:
                raise ValueError("seed grant belongs to another server")
            if grant.status not in ("queued", "prepared"):
                return "already_confirmed" if grant.status == "confirmed" else grant.status
            prepared = grant.status == "prepared"
            if not prepared:
                unresolved = session.scalar(
                    select(SeedVipGrant.id).where(
                        SeedVipGrant.server_number == server_number,
                        SeedVipGrant.player_id == player_id,
                        SeedVipGrant.preview.is_(False),
                        SeedVipGrant.status.in_(["prepared", "review"]),
                        SeedVipGrant.id != grant_id,
                    ).limit(1)
                )
                other_unresolved = session.scalar(
                    select(VipRewardGrant.id).where(
                        VipRewardGrant.server_number == server_number,
                        VipRewardGrant.player_id == player_id,
                        VipRewardGrant.preview.is_(False),
                        VipRewardGrant.status.in_(["prepared", "review"]),
                    ).limit(1)
                )
                if unresolved is not None or other_unresolved is not None:
                    # This grant was never attempted. Keep it queued so it can
                    # resume after the earlier uncertain write is reviewed.
                    grant.reason = "blocked_by_unresolved_vip_write"
                    grant.updated_at = datetime.now(timezone.utc)
                    return "blocked"
                reward_time = expiration(grant.reward_time)
                duration = timedelta(seconds=grant.reward_seconds)
                cumulative = grant.cumulative
                player_name = grant.player_name
            else:
                target = expiration(grant.target)
                description = grant.description

        if not prepared:
            # RCON reads may themselves query PostgreSQL. Do not hold a second
            # journal transaction while making those calls under the VIP lock.
            vip = vip_for_reward(rcon, player_id, player_name)
            if permanent(vip):
                with maker() as session, session.begin():
                    grant = session.get(SeedVipGrant, grant_id, with_for_update=True)
                    if grant.status == "queued":
                        grant.status = "skipped"
                        grant.reason = "permanent_vip"
                        grant.updated_at = datetime.now(timezone.utc)
                    return grant.status
            previous = expiration(vip["vip_expiration"]) if vip else None
            if cumulative:
                target = max(previous, reward_time) + duration if previous else reward_time + duration
            else:
                target = max(previous, reward_time + duration) if previous else reward_time + duration
            description = vip["name"] if vip else player_name
            with maker() as session, session.begin():
                grant = session.get(SeedVipGrant, grant_id, with_for_update=True)
                if grant.status != "queued":
                    return grant.status
                grant.target = target
                grant.description = description
                grant.status = "prepared"
                grant.reason = None
                grant.updated_at = datetime.now(timezone.utc)

        if prepared:
            vip = current_vip(rcon, player_id)
            matched = bool(vip and vip["vip_expiration"] is not None and
                           abs((expiration(vip["vip_expiration"]) - target).total_seconds()) < 1)
            with maker() as session, session.begin():
                grant = session.get(SeedVipGrant, grant_id, with_for_update=True)
                if grant.status == "prepared":
                    grant.status = "confirmed" if matched else "review"
                    grant.reason = "reconciled" if matched else "uncertain_write"
                    grant.updated_at = datetime.now(timezone.utc)
                return grant.status

        result = rcon.add_vip(player_id=player_id, description=description, expiration=target.isoformat())
        if result is False:
            with maker() as session, session.begin():
                grant = session.get(SeedVipGrant, grant_id, with_for_update=True)
                if grant.status == "prepared":
                    grant.status = "rejected"
                    grant.reason = "server_rejected"
                    grant.updated_at = datetime.now(timezone.utc)
                return grant.status
        if result is not True:
            return "prepared"
        vip = current_vip(rcon, player_id)
        matched = bool(vip and vip["vip_expiration"] is not None and
                       abs((expiration(vip["vip_expiration"]) - target).total_seconds()) < 1)
        with maker() as session, session.begin():
            grant = session.get(SeedVipGrant, grant_id, with_for_update=True)
            if grant.status == "prepared":
                grant.status = "confirmed" if matched else "review"
                grant.reason = None if matched else "readback_mismatch"
                grant.updated_at = datetime.now(timezone.utc)
            return grant.status
