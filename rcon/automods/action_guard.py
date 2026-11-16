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

from rcon.automods import event_guard
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
    CheckConstraint("action IN ('message', 'punish', 'kick', 'switch', 'ban')", name="ck_automod_guard_action"),
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


def _expected_event_rules(session, server_number: int, player_id: str, token: str) -> int | None:
    reserved = session.execute(select(action_guard_history.c.reason, action_guard_history.c.rules_json).where(
        action_guard_history.c.server_number == server_number,
        action_guard_history.c.player_id == player_id,
        action_guard_history.c.token == token,
        action_guard_history.c.event == 'reserved',
    )).one_or_none()
    if reserved is not None and reserved.reason and reserved.reason.startswith('event:'):
        rules = json.loads(reserved.rules_json)
        if not isinstance(rules, list) or not rules:
            raise RuntimeError('Invalid event reservation history')
        return len(rules)
    return None


def reserve(server_number: int, player_id: str, rules: list[str], action: str,
            *, legacy_global: bool = False, event: tuple[int, str] | None = None) -> str | None:
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
            or action not in {"message", "punish", "kick", "switch", "ban"}):
        raise ValueError("Invalid automated action reservation")
    if event is not None:
        event_ms, event_key = event
        if (legacy_global or not isinstance(event_ms, int) or isinstance(event_ms, bool)
                or event_ms <= 0 or not isinstance(event_key, str) or len(event_key) != 64
                or any(char not in '0123456789abcdef' for char in event_key)):
            raise ValueError("Invalid automated action event")
        if not event_guard.allow_after_cutover(server_number, event_ms, _lock):
            return None
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
        event_rows = []
        if event is not None:
            event_rows = session.execute(select(event_guard.events).where(
                event_guard.events.c.server_number == server_number,
                event_guard.events.c.player_id == player_id,
                event_guard.events.c.event_key == event_key,
                event_guard.events.c.rule.in_(rules),
            ).with_for_update()).mappings().all()
            # A manually reviewed uncertain action can release future events,
            # but the same historical event must never be replayed.
            if any(row['state'] != 'rejected' for row in event_rows):
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
        if event is not None:
            event_values = dict(token=token, state='pending', updated_at=now, event_ms=event_ms)
            existing_event_rules = {row['rule'] for row in event_rows if row['action'] == action}
            for rule in rules:
                if rule not in existing_event_rules:
                    session.execute(event_guard.events.insert().values(server_number=server_number,
                        player_id=player_id, event_key=event_key, rule=rule, action=action, **event_values))
                else:
                    session.execute(update(event_guard.events).where(
                        event_guard.events.c.server_number == server_number,
                        event_guard.events.c.player_id == player_id,
                        event_guard.events.c.event_key == event_key,
                        event_guard.events.c.rule == rule,
                        event_guard.events.c.action == action).values(**event_values))
        session.execute(action_guard_history.insert().values(
            id=uuid.uuid4().hex, server_number=server_number, player_id=player_id, token=token,
            event="reserved", rules_json=json.dumps(rules), action=action, created_at=now,
            reason=(f"event:{event_key}" if event is not None else
                    "Legacy actions may have unresolved outcomes" if legacy_global else None)))
    return token


def pending_players(server_number: int, rule: str) -> set[str]:
    """Return every unresolved player for a rule, including a global hold."""
    if not 1 <= server_number <= 32 or not rule or len(rule) > 150:
        raise ValueError("Invalid server or rule")
    with get_session_maker()() as session:
        return set(session.execute(select(action_guard.c.player_id).where(
            action_guard.c.server_number == server_number,
            action_guard.c.rule == rule,
            action_guard.c.state == 'pending',
        )).scalars())


def finish(server_number: int, player_id: str, token: str, result: str, *, expected: int | None = None,
           event_expected: int | None = None) -> int:
    """Finish only a confirmed or explicitly rejected action."""
    if result not in {"confirmed", "rejected"} or not token:
        raise ValueError("Invalid action result")
    with get_session_maker()() as session, session.begin():
        _lock(session, server_number, player_id)
        stored_event_expected = _expected_event_rules(session, server_number, player_id, token)
        if stored_event_expected is not None:
            if event_expected is not None and event_expected != stored_event_expected:
                raise RuntimeError("Invalid expected event rule count")
            event_expected = stored_event_expected
        result_set = session.execute(update(action_guard).where(
            action_guard.c.server_number == server_number, action_guard.c.player_id == player_id,
            action_guard.c.token == token, action_guard.c.state == "pending",
        ).values(state=result, updated_at=datetime.now(timezone.utc)))
        if expected is not None and result_set.rowcount != expected:
            raise RuntimeError("Could not finish all reserved rules")
        if result_set.rowcount and event_expected is not None:
            event_result = session.execute(update(event_guard.events).where(
                event_guard.events.c.server_number == server_number,
                event_guard.events.c.player_id == player_id,
                event_guard.events.c.token == token,
                event_guard.events.c.state == 'pending',
            ).values(state=result, updated_at=datetime.now(timezone.utc)))
            if event_result.rowcount != event_expected:
                raise RuntimeError("Could not finish all reserved event rules")
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
        expected_events = _expected_event_rules(session, server_number, player_id, token)
        result = session.execute(update(action_guard).where(
            action_guard.c.server_number == server_number, action_guard.c.player_id == player_id,
            action_guard.c.token == token, action_guard.c.state == "pending",
        ).values(state="reviewed", updated_at=datetime.now(timezone.utc),
                 reviewed_by=actor.strip(), review_reason=reason.strip()))
        if result.rowcount and expected_events is not None:
            event_result = session.execute(update(event_guard.events).where(
                event_guard.events.c.server_number == server_number,
                event_guard.events.c.player_id == player_id,
                event_guard.events.c.token == token,
                event_guard.events.c.state == 'pending',
            ).values(state='reviewed', updated_at=datetime.now(timezone.utc)))
            if event_result.rowcount != expected_events:
                raise RuntimeError("Could not review all reserved event rules")
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
