"""Persistent, fail-closed reservations for uncertain automated actions.

The automod execution path uses these reservations to prevent retries when
the outcome of an earlier action is uncertain.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, MetaData, String, Table, Text, func, select, text, update

from rcon.models import get_session_maker

metadata = MetaData()
action_guard = Table(
    "automod_action_guard", metadata,
    Column("server_number", Integer, primary_key=True),
    Column("player_id", String(100), primary_key=True),
    Column("rule", String(150), primary_key=True),
    Column("action", String(20), primary_key=True),
    Column("token", String(32), nullable=False, index=True),
    Column("state", String(20), nullable=False, index=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("reviewed_by", String(150), nullable=True),
    Column("review_reason", Text, nullable=True),
    CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_automod_guard_server"),
    CheckConstraint("action IN ('message', 'punish', 'kick')", name="ck_automod_guard_action"),
    CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name="ck_automod_guard_state"),
)
action_guard_history = Table(
    "automod_action_guard_history", metadata,
    Column("id", String(32), primary_key=True),
    Column("server_number", Integer, nullable=False, index=True),
    Column("player_id", String(100), nullable=False),
    Column("token", String(32), nullable=False, index=True),
    Column("event", String(20), nullable=False),
    Column("rules_json", Text, nullable=True),
    Column("action", String(20), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("actor", String(150), nullable=True),
    Column("reason", Text, nullable=True),
    CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_automod_guard_history_server"),
    CheckConstraint("event IN ('reserved', 'confirmed', 'rejected', 'reviewed')", name="ck_automod_guard_history_event"),
)


def _lock(session, server_number: int, player_id: str) -> None:
    if session.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(hashlib.sha256(f"automod-action:{server_number}:{player_id}".encode()).digest()[:8],
                             "big", signed=True)
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def reserve(server_number: int, player_id: str, rules: list[str], action: str,
            *, legacy_global: bool = False) -> str | None:
    """Reserve all originating rules, or reject the whole group if uncertain.

    Pending reservations deliberately survive reconnects and worker restarts.
    They require a confirmed result or an explicit audited operator decision.
    A legacy-wide hold may only be created while all automod workers for the
    server are stopped; it blocks that rule for every player until review.
    """
    rules = sorted(set(rules))
    if (not 1 <= server_number <= 32 or not player_id or len(player_id) > 100
            or (player_id == "*") != legacy_global
            or not rules or any(not rule or len(rule) > 150 for rule in rules)
            or action not in {"message", "punish", "kick"}):
        raise ValueError("Invalid automated action reservation")
    token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        rows = session.execute(select(action_guard).where(
            action_guard.c.server_number == server_number,
            action_guard.c.player_id.in_([player_id, "*"]),
            action_guard.c.rule.in_(rules),
        ).with_for_update()).mappings().all()
        if any(row["state"] == "pending" for row in rows):
            return None
        existing = {(row["rule"], row["action"]) for row in rows if row["player_id"] == player_id}
        for rule in rules:
            values = dict(token=token, state="pending", updated_at=now, reviewed_by=None, review_reason=None)
            if (rule, action) in existing:
                session.execute(update(action_guard).where(
                    action_guard.c.server_number == server_number, action_guard.c.player_id == player_id,
                    action_guard.c.rule == rule, action_guard.c.action == action).values(**values))
            else:
                session.execute(action_guard.insert().values(server_number=server_number, player_id=player_id,
                                                            rule=rule, action=action, **values))
        session.execute(action_guard_history.insert().values(
            id=uuid.uuid4().hex, server_number=server_number, player_id=player_id, token=token,
            event="reserved", rules_json=json.dumps(rules), action=action, created_at=now,
            reason="Legacy actions may have unresolved outcomes" if legacy_global else None))
    return token


def finish(server_number: int, player_id: str, token: str, result: str, *, expected: int | None = None) -> int:
    """Finish only a confirmed or explicitly rejected action."""
    if result not in {"confirmed", "rejected"} or not token:
        raise ValueError("Invalid action result")
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        result_set = session.execute(update(action_guard).where(
            action_guard.c.server_number == server_number, action_guard.c.player_id == player_id,
            action_guard.c.token == token, action_guard.c.state == "pending",
        ).values(state=result, updated_at=datetime.now(timezone.utc)))
        if expected is not None and result_set.rowcount != expected:
            raise RuntimeError("Could not finish all reserved rules")
        if result_set.rowcount:
            session.execute(action_guard_history.insert().values(
                id=uuid.uuid4().hex, server_number=server_number, player_id=player_id, token=token,
                event=result, created_at=datetime.now(timezone.utc)))
        return result_set.rowcount


def review(server_number: int, player_id: str, token: str, actor: str, reason: str) -> int:
    if not actor or not actor.strip() or len(actor) > 150 or not reason or not reason.strip() or len(reason) > 1000:
        raise ValueError("An operator and reason are required")
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        result = session.execute(update(action_guard).where(
            action_guard.c.server_number == server_number, action_guard.c.player_id == player_id,
            action_guard.c.token == token, action_guard.c.state == "pending",
        ).values(state="reviewed", updated_at=datetime.now(timezone.utc),
                 reviewed_by=actor.strip(), review_reason=reason.strip()))
        if result.rowcount:
            session.execute(action_guard_history.insert().values(
                id=uuid.uuid4().hex, server_number=server_number, player_id=player_id, token=token,
                event="reviewed", created_at=datetime.now(timezone.utc), actor=actor.strip(), reason=reason.strip()))
        return result.rowcount


def list_pending(server_number: int, limit: int = 50) -> dict:
    """List complete action groups without exposing other servers' entries."""
    if not 1 <= server_number <= 32 or not 1 <= limit <= 100:
        raise ValueError("Invalid server or pagination")
    with get_session_maker()() as session:
        groups = session.execute(select(
            action_guard.c.token, action_guard.c.player_id,
            func.min(action_guard.c.updated_at).label("updated_at"),
        ).where(action_guard.c.server_number == server_number, action_guard.c.state == "pending")
            .group_by(action_guard.c.token, action_guard.c.player_id)
            .order_by(func.min(action_guard.c.updated_at), action_guard.c.token).limit(limit + 1)).all()
        visible = groups[:limit]
        tokens = [row.token for row in visible]
        rows = session.execute(select(action_guard).where(
            action_guard.c.server_number == server_number, action_guard.c.state == "pending",
            action_guard.c.token.in_(tokens)).order_by(action_guard.c.rule)).mappings().all() if tokens else []
        details = {}
        for row in rows:
            details.setdefault(row["token"], []).append({"rule": row["rule"], "action": row["action"]})
        return {"results": [{"token": row.token, "player_id": row.player_id,
                             "updated_at": row.updated_at.isoformat(), "actions": details[row.token]}
                            for row in visible], "more": len(groups) > limit}
