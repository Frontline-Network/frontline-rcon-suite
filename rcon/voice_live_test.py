"""A single consensual pilot kick, tied to one new report and two live sessions."""

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
    from rcon import voice_reports as voice

    if not voice.enabled(server) or voice.live_kicks_enabled(server):
        raise ValueError(
            "The voice pilot must be enabled and global voice kicks disabled"
        )
    if target == reporter or not all(
        re.fullmatch(r"[0-9a-f]{32}", p) for p in (target, reporter)
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
        for pid in (target, reporter):
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
        target_seat = voice.communication_identity(participants[target][0], True)
        if not voice._channel(participants[reporter][0], target_seat):
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
            "state": "armed",
            "started_at": now,
            "expires_at": now + WINDOW_SECONDS,
            "round_id": context["round_id"],
            "target_id": target,
            "reporter_id": reporter,
            "session": participants[target][1],
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
        if state in {"armed", "bound"} and time.time() >= window["expires_at"]:
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
            if not event or event.payload.get("status") != "sending":
                raise ValueError(
                    "Test dispatch already finished; there is nothing to cancel"
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


def allowed(sess, event, stage, now):
    """Caller holds the same server lock and independently validates a fresh game context."""
    from rcon import voice_reports as voice

    server = event.incident.server_number
    p = event.payload
    grant = p["voice"].get("live_test")
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
        p["voice"].get("live_test")
        and p["mode"] == "active"
        and not allowed(sess, event, "reserve", now)
    ):
        event.payload = {**p, "mode": "dry_run"}
