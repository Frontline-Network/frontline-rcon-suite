"""Operator-scoped voice pilots bound to live game identities and new reports."""

import re
import time
from uuid import uuid4

from sqlalchemy import func, select

from rcon import report_admin as admin
from rcon.models import AdminIncident, AdminIncidentEvent, UserConfig

WINDOW_SECONDS = 600


def _window(sess, server):
    return sess.scalar(
        select(UserConfig).where(UserConfig.key == f"{server}_voice_live_test_window")
    )


def arm(server, target, reporter, context):
    return _arm(server, target, reporter, context, WINDOW_SECONDS)


def arm_chat(server, reporter, context, minutes):
    if not 1 <= minutes <= 60:
        raise ValueError("Select a chat pilot duration between 1 and 60 minutes")
    return _arm(server, None, reporter, context, minutes * 60)


def _arm(server, target, reporter, context, duration):
    from rcon import voice_reports as voice

    if not voice.enabled(server) or voice.live_kicks_enabled(server):
        raise ValueError(
            "The voice pilot must be enabled and global voice kicks disabled"
        )
    ids = (reporter,) if target is None else (target, reporter)
    if target == reporter or not all(
        re.fullmatch(r"[0-9a-f]{32}", p) for p in ids
    ):
        raise ValueError("Use two different canonical Vietnam EOS player IDs")
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        now = time.time()
        if not admin.valid_context(context, now):
            raise ValueError("A fresh roster and current round are required")
        cfg = admin.config(sess, server)
        if not (cfg.enabled and cfg.communication and cfg.mode == "active"):
            raise ValueError(
                "The existing communication rule must be enabled and active"
            )
        participants = {}
        for pid in ids:
            rows = [
                p
                for p in context["players"]
                if p.get("player_id") == pid and p.get("online") is not False
            ]
            token = admin.session_token(sess, server, pid, now)
            if len(rows) != 1 or token is None:
                raise ValueError(
                    "Both volunteers need a verified current session on this server"
                )
            participants[pid] = (rows[0], token)
        target_seat = voice.communication_identity(participants[target][0], True) if target else None
        if target and not voice._channel(participants[reporter][0], target_seat):
            raise ValueError(
                "The reporter must be in the target's squad or leadership voice channel"
            )
        row = _window(sess, server)
        if row and row.value["expires_at"] > now and row.value["state"] != "cancelled":
            raise ValueError("An unexpired test window already exists")
        high_water = (
            sess.scalar(
                select(func.max(AdminIncidentEvent.id))
                .join(AdminIncident)
                .where(AdminIncident.server_number == server)
            )
            or 0
        )
        window = {
            "id": str(uuid4()),
            "state": "armed" if target else "chat",
            "started_at": now,
            "expires_at": now + duration,
            "round_id": context["round_id"],
            "target_id": target,
            "reporter_id": reporter,
            "session": participants[target][1] if target else None,
            "reporter_session": participants[reporter][1],
            "target_seat": target_seat,
            "witness_seat": voice.communication_identity(
                participants[reporter][0], True
            ),
            "after_event": high_water,
            "incident_id": None,
        }
        if row is None:
            sess.add(UserConfig(key=f"{server}_voice_live_test_window", value=window))
        else:
            row.value = window
        return window["id"]


def inspect_window(server):
    with admin.enter_session() as sess:
        row = _window(sess, server)
        if not row:
            return {"state": "absent"}
        window = row.value
        state = window["state"]
        if state in {"armed", "bound", "chat"} and time.time() >= window["expires_at"]:
            state = "expired"
        return {
            "state": state,
            "window": window["id"],
            "expires_at": window["expires_at"],
            "case": window.get("incident_id"),
        }


def cancel(server, window_id):
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        row = _window(sess, server)
        if not row or row.value["id"] != window_id:
            raise ValueError("Window does not match the currently registered test")
        if row.value["state"] == "consumed":
            case_id = row.value["incident_id"]
            event = sess.scalar(
                select(AdminIncidentEvent).where(
                    AdminIncidentEvent.incident_id == case_id,
                    AdminIncidentEvent.event_type == "report_admin",
                )
            )
            if (
                not event or event.payload.get("status") != "sending"
                or event.payload.get("kick_started_at") is not None
            ):
                raise ValueError(
                    "Test dispatch has started or finished; there is nothing to cancel"
                )
        row.value = {**row.value, "state": "cancelled", "cancelled_at": time.time()}


def _matches(sess, event, row, now):
    p, i, v = event.payload, event.incident, event.payload["voice"]
    if not row:
        return False
    w = row.value
    return (
        w["started_at"] <= p["report_time"] <= now < w["expires_at"]
        and event.id > w["after_event"]
        and w["round_id"] == p["round_id"]
        and w["target_id"] == p["target_id"] == i.target_id
        and w["reporter_id"] == i.reporter_id == v.get("witness_id")
        and not v.get("external")
        and w["target_seat"] == p["target"]["seat"]
        and w["witness_seat"] == v.get("witness_seat")
        and w["session"]
        == p["session"]
        == admin.session_token(sess, i.server_number, w["target_id"], now)
        and w["reporter_session"]
        == p["reporter_session"]
        == v.get("witness_session")
        == admin.session_token(sess, i.server_number, w["reporter_id"], now)
    )


def bind(sess, event, now):
    """Under server lock: never upgrade an older case or re-use an abandoned grant."""
    p = event.payload
    if p["config"]["mode"] != "active":
        return
    row = _window(sess, event.incident.server_number)
    if row and row.value["state"] == "chat" and _matches_chat(sess, event, row.value, now):
        event.payload = {
            **p,
            "mode": "active",
            "voice": {**p["voice"], "chat_pilot": row.value["id"]},
        }
        return
    if row and row.value["state"] == "armed" and _matches(sess, event, row, now):
        row.value = {
            **row.value,
            "state": "bound",
            "incident_id": event.incident_id,
            "bound_at": now,
        }
        event.payload = {
            **p,
            "mode": "active",
            "voice": {**p["voice"], "live_test": row.value["id"]},
        }


def _matches_chat(sess, event, window, now):
    incident, p = event.incident, event.payload
    return (
        incident.source == "chat"
        and incident.reporter_id == window["reporter_id"]
        and p["rule"] == "communication"
        and window["started_at"] <= p["report_time"] <= now < window["expires_at"]
        and event.id > window["after_event"]
        and p["round_id"] == window["round_id"]
        and p["reporter_session"] == window["reporter_session"]
        and admin.session_token(sess, incident.server_number, incident.reporter_id, now)
        == window["reporter_session"]
    )


def allowed(sess, event, stage, now):
    """Caller holds the same server lock and independently validates a fresh game context."""
    from rcon import voice_reports as voice

    server = event.incident.server_number
    p = event.payload
    grant = p["voice"].get("live_test")
    chat = p["voice"].get("chat_pilot")
    if chat:
        row = _window(sess, server)
        return bool(
            voice.enabled(server) and p["mode"] == "active" and row
            and row.value["state"] == "chat" and row.value["id"] == chat
            and _matches_chat(sess, event, row.value, now)
        )
    if not grant:
        return p["mode"] == "active" and voice.live_kicks_enabled(server)
    if (
        not voice.enabled(server)
        or voice.live_kicks_enabled(server)
        or p["mode"] != "active"
    ):
        return False
    row = _window(sess, server)
    expected = "consumed" if stage == "dispatch" else "bound"
    return bool(
        row
        and row.value["id"] == grant
        and row.value["state"] == expected
        and row.value["incident_id"] == event.incident_id
        and _matches(sess, event, row, now)
        and time.time() < row.value["expires_at"]
    )


def consume(sess, event, now):
    """Persist consumption atomically with the ordinary no-retry sending reservation."""
    if not event.payload["voice"].get("live_test"):
        return True
    if not allowed(sess, event, "reserve", now):
        return False
    row = _window(sess, event.incident.server_number)
    row.value = {**row.value, "state": "consumed", "consumed_at": now}
    return True


def keep_or_simulate(sess, event, now):
    """Freeze a revoked/expired grant to dry-run even if a new window is armed later."""
    p = event.payload
    if (
        (p["voice"].get("live_test") or p["voice"].get("chat_pilot"))
        and p["mode"] == "active"
        and not allowed(sess, event, "reserve", now)
    ):
        event.payload = {**p, "mode": "dry_run"}
