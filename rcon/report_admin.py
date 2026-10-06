"""Opt-in report rules, persisted in the existing incident event journal.

No model, ban, warning, vote, or free-form game command. A durable send marker
precedes the single kick attempt. Manual incident actions share the server lock.
The normal Discord outbox publishes every result; uncertain results stay open.
"""

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import or_, select, text

from rcon.leadership_vote import storage as votes
from rcon.leadership_vote.domain import identity
from rcon.leadership_vote.service import read_context
from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    AdminIncidentDiscordDelivery,
    PlayerID,
    PlayerSession,
    UserConfig,
    MessageTemplate,
    LeadershipVote,
    LeadershipMessage,
)
from rcon.report_admin_rules import (
    classify,
    target_for,
    unique_seat,
    QUALIFIED,
    MAX_REPORT_AGE,
)
from rcon import report_admin_evidence as evidence_rules
from rcon.admin_incidents import _normalize_team, _normalize_message
from rcon.user_config.report_admin import ReportAdminUserConfig as Config
from rcon.user_config.utils import _invalidate_user_config_cache

logger = logging.getLogger(__name__)
ACTOR = "system:report-admin"
OPEN = {"queued", "waiting", "sending"}
enter_session = votes.enter_session  # Commit errors must propagate.


def utc(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc)


def key(server):
    return f"{server}_ReportAdminUserConfig"


def config(sess, server):
    row = sess.scalar(select(UserConfig).where(UserConfig.key == key(server)))
    return Config.model_validate(row.value) if row else Config()


def pending(sess, server, limit=None, due_at=None):
    query = (
        select(AdminIncidentEvent)
        .join(AdminIncident)
        .where(
            AdminIncident.server_number == server,
            AdminIncidentEvent.event_type == "report_admin",
            AdminIncidentEvent.payload["status"].as_string().in_(OPEN),
        )
        .order_by(AdminIncidentEvent.id)
    )
    if due_at is not None:
        query = query.where(
            or_(
                AdminIncidentEvent.payload["status"].as_string() != "waiting",
                AdminIncidentEvent.payload["ready_at"].as_float() <= due_at,
                AdminIncidentEvent.payload["report_time"].as_float()
                <= due_at - evidence_rules.CASE_TTL,
            )
        )
    if limit is not None:
        query = query.limit(limit)
    return sess.scalars(query).all()


def summary(payload):
    return {
        k: payload[k]
        for k in (
            "status",
            "mode",
            "rule",
            "target_id",
            "target_name",
            "result",
            "teamkill_count",
            "teamkill_log_ids",
            "window_seconds",
            "updated_at",
            "assessment",
            "ready_at",
        )
        if k in payload
    }


def publish(sess, event, status, reason, **extra):
    stamp = time.time()
    event.payload = {
        **event.payload,
        **extra,
        "status": status,
        "result": reason,
        "updated_at": stamp,
    }
    incident = event.incident
    incident.revision += 1
    incident.updated_at = utc(stamp)
    incident.events.append(
        AdminIncidentEvent(
            actor=ACTOR,
            event_type="report_admin_" + status,
            payload=summary(event.payload),
            created_at=utc(stamp),
        )
    )
    if status == "kicked":
        incident.status, incident.assigned_to, incident.resolved_at = (
            "resolved",
            ACTOR,
            utc(stamp),
        )


def configure(server, cfg, actor=ACTOR):
    with enter_session() as sess:
        votes.lock(sess, server)
        for template_id in (cfg.communication_template_id, cfg.teamkills_template_id):
            if template_id is not None:
                template = sess.get(MessageTemplate, template_id)
                if not template or str(template.category) != "REASON":
                    raise ValueError("Select an existing REASON message template")
        if cfg.enabled:
            from rcon.leadership_vote.domain import OPEN as VOTE_OPEN

            for vote in sess.scalars(
                select(LeadershipVote).where(
                    LeadershipVote.server_number == server,
                    LeadershipVote.status.in_(VOTE_OPEN),
                )
            ):
                if vote.payload.get("execution", {}).get("send_started_at") is not None:
                    from rcon.admin_incidents import IncidentConflict

                    raise IncidentConflict(
                        "Wait for the in-progress leadership kick before changing report routing"
                    )
                votes.finish(
                    sess,
                    vote,
                    "cancelled",
                    "Report-Admin aktiviert / Report admin enabled",
                    time.time(),
                    actor,
                )
        row = sess.scalar(select(UserConfig).where(UserConfig.key == key(server)))
        if row is None:
            row = UserConfig(key=key(server), value=cfg.model_dump())
            sess.add(row)
        else:
            row.value = cfg.model_dump()
        # Never resume queued reports when settings are changed/re-enabled.
        for event in pending(sess, server):
            publish(sess, event, "manual", "Einstellungen geändert / Settings changed")
    _invalidate_user_config_cache(key(server))


def kick_reason(sess, payload):
    """Only administrator-selected text and fixed placeholders; no eval/format."""
    default = (
        "Gemeldete fehlende Führungskommunikation / Reported lack of leadership communication"
        if payload["rule"] == "communication"
        else "Belegter Teamkill mit ausdrücklicher eigener Absichtserklärung / Recorded teamkill with explicit first-person admission"
    )
    template_id = payload["config"].get(payload["rule"] + "_template_id")
    template = sess.get(MessageTemplate, template_id) if template_id else None
    if not template or str(template.category) != "REASON":
        return default
    value = template.content
    for name, replacement in {
        "player_name": payload["target_name"],
        "teamkills": str(payload.get("teamkill_count", 0)),
        "minutes": str(round(payload.get("window_seconds", 0) / 60, 1)),
    }.items():
        value = value.replace("{" + name + "}", replacement)
    return " ".join(value.split())[:500] or default


def session_token(sess, server, pid, stamp):
    row = sess.scalar(
        select(PlayerSession)
        .join(PlayerID)
        .where(
            PlayerID.player_id == pid,
            PlayerSession.server_number == server,
        )
        .order_by(PlayerSession.start.desc(), PlayerSession.id.desc())
        .limit(1)
    )
    if row is None or row.end is not None or row.start is None:
        return None
    start = row.start.replace(tzinfo=timezone.utc).timestamp()
    return row.id if start <= stamp else None


def valid_context(context, now):
    try:
        return bool(
            context
            and context["round_id"]
            and isinstance(context["players"], list)
            and 0 <= now - context["captured_at"] <= 10
            and 0 < context["round_start"] <= now
        )
    except (KeyError, TypeError, ValueError):
        return False


def enqueue(sess, incident, context, now):
    """True means this server uses report-admin routing, not leadership votes."""
    cfg = config(sess, incident.server_number)
    if not cfg.enabled:
        return False
    data = incident.to_dict()
    players = (context or {}).get("players", [])
    rule = classify(incident.raw_message, players)
    if incident.source != "chat" or not rule or not getattr(cfg, rule):
        return True  # All other subjects remain strictly manual in this mode.
    resolution_subjects = data.get("subjects", [])
    target = target_for(data, players, rule, allow_self_reports=cfg.allow_self_reports)
    if not target and not any(
        s.get("state") in {"confirmed", "rejected"} for s in data.get("subjects", [])
    ):
        # Dedicated typo candidates; do not weaken ordinary incident parsing.
        from rcon.admin_incidents import parse_chat_report

        parsed = parse_chat_report(
            incident.raw_message,
            current_players=players,
            reporter_context=incident.reporter_context,
            fuzzy_threshold=0.70,
            context_mode="enabled",
        )
        if parsed:
            target = target_for(
                {**data, "subjects": parsed["subjects"]},
                players,
                rule,
                allow_self_reports=cfg.allow_self_reports,
            )
            if target:
                resolution_subjects = parsed["subjects"]
    stamp = (context or {}).get("event_time")
    payload = {
        "status": "manual",
        "mode": cfg.mode,
        "rule": rule,
        "result": "Nicht eindeutig prüfbar / Cannot validate safely",
        "updated_at": now,
    }
    event = AdminIncidentEvent(
        actor=ACTOR,
        event_type="report_admin",
        payload=payload,
        idempotency_key=f"report-admin:{incident.id}",
        created_at=utc(now),
    )
    incident.events.append(event)
    if (
        not valid_context(context, now)
        or not isinstance(stamp, (int, float))
        or not 0 <= now - stamp <= 30
        or not target
    ):
        return True
    token = session_token(sess, incident.server_number, target["player_id"], stamp)
    reporter_token = session_token(
        sess, incident.server_number, incident.reporter_id, stamp
    )
    if token is None or reporter_token is None:
        return True
    # Require a configured Discord destination; no silent moderation when unpaired.
    if not votes.discord_ready(sess):
        return True
    from rcon.admin_incidents import _subject_from_payload, player_snapshot

    # Validation must not replace the report's statistics with routing metadata.
    # Use the very same fresh, uniquely identified roster row as the decision;
    # never borrow a similarly named player's or a previous round's statistics.
    target_snapshot = player_snapshot(
        next(p for p in players if str(p.get("player_id")) == target["player_id"])
    )

    for subject in incident.subjects:
        subject.is_primary = False
    incident.subjects.append(
        _subject_from_payload(
            {
                "kind": "player",
                "state": "confirmed",
                "is_primary": True,
                "player_id": target["player_id"],
                "display_name": target["name"],
                "team": target["team"],
                "match_method": "report_admin_validated",
                "parser_version": "report-admin-1",
                "snapshot": {
                    **target_snapshot,
                    "rule": rule,
                    "seat": target["seat"],
                    "candidates": [
                        {
                            k: s.get(k)
                            for k in (
                                "kind",
                                "state",
                                "player_id",
                                "match_method",
                                "matched_text",
                                "confidence",
                            )
                        }
                        for s in resolution_subjects
                    ],
                },
            },
            actor=ACTOR,
        )
    )
    incident.target_id, incident.target_name = target["player_id"], target["name"]
    event.payload = {
        **payload,
        "status": "queued",
        "result": "Prüfung ausstehend / Awaiting checks",
        "target_id": target["player_id"],
        "target_name": target["name"],
        "target": target,
        "session": token,
        "reporter_session": reporter_token,
        "reporter_team": _normalize_team(
            next(
                p for p in players if str(p.get("player_id")) == incident.reporter_id
            ).get("team")
        ),
        "report_time": stamp,
        "round_id": context["round_id"],
        "round_start": context["round_start"],
        "config": cfg.model_dump(),
        "incident_revision": incident.revision,
    }
    return True


def delivered(sess, incident_id):
    return (
        sess.scalar(
            select(AdminIncidentDiscordDelivery.id)
            .join(AdminIncidentEvent)
            .where(
                AdminIncidentEvent.incident_id == incident_id,
                AdminIncidentEvent.event_type == "created",
                AdminIncidentDiscordDelivery.delivered_at.is_not(None),
            )
            .limit(1)
        )
        is not None
    )


def role_history(payload):
    """Optional observed history; never project the current role into the past."""
    from rcon.utils import MapsHistory

    try:
        history = MapsHistory().get_current_map() or {}
        if history.get("start") != payload["round_start"] or history.get("end"):
            return []
        rows = (
            history.get("player_stats", {}).get(payload["target_id"], {}).get("units")
            or []
        )
        return [
            {
                "at": payload["round_start"] + row["ts"],
                "role": row["role"],
                "team": row["team"],
                "squad": row["squad"],
            }
            for row in rows
            if isinstance(row.get("ts"), (float, int))
            and 0 <= row["ts"] <= time.time() - payload["round_start"]
        ][-40:]
    except Exception:
        logger.warning("Report-admin role history unavailable")
        return []


def assess(sess, server, event, live, now):
    p = event.payload
    case = evidence_rules.collect(
        sess, server, p, event.incident.reporter_id, now, live
    )
    if p["rule"] == "teamkills":
        result = evidence_rules.assess_teamkills(
            case, p["target_id"], event.incident.reporter_id, p["report_time"], now
        )
        if result[0] == "eligible" and QUALIFIED.search(
            _normalize_message(event.incident.raw_message)
        ):
            return (
                "manual",
                "Eingeschränkte oder widersprüchliche Meldung / Qualified or conflicting report",
                result[2],
            )
        return result
    result = evidence_rules.assess_cheating(case, p["target_id"], role_history(p))
    reporters = set(
        sess.scalars(
            select(AdminIncident.reporter_id)
            .join(AdminIncidentEvent)
            .where(
                AdminIncident.server_number == server,
                AdminIncident.target_id == p["target_id"],
                AdminIncident.created_at >= utc(now - evidence_rules.LOOKBACK),
                AdminIncidentEvent.event_type == "report_admin",
                AdminIncidentEvent.payload["rule"].as_string() == "cheating",
            )
        )
    ) - {None, ""}
    result[2]["assessment"]["distinct_reporters"] = len(reporters)
    if len(reporters) > 1:
        result[2]["assessment"]["priority"] = "high"
        result[2]["assessment"]["reasons"].append(
            "Mehrere Melder: Priorität erhöht, kein zusätzlicher Cheatbeweis / Multiple reporters raise priority, not certainty"
        )
    return result


def invalid_reason(sess, event, context, now):
    i, p = event.incident, event.payload
    cfg = config(sess, i.server_number)
    if not cfg.enabled or cfg.model_dump() != p["config"]:
        return "Einstellungen geändert / Settings changed"
    if (
        i.status != "new"
        or i.assigned_to
        or i.target_id != p["target_id"]
        or i.revision != p["incident_revision"]
    ):
        return "Admin-Bearbeitung oder Ziel geändert / Admin handling or target changed"
    max_age = evidence_rules.CASE_TTL if p["rule"] == "teamkills" else MAX_REPORT_AGE
    if not 0 <= now - p["report_time"] <= max_age:
        return "Report abgelaufen / Report expired"
    if not valid_context(context, now) or context["round_id"] != p["round_id"]:
        return "Veraltete Daten oder Kartenwechsel / Stale data or map changed"
    players = context["players"]
    ids = [str(q.get("player_id") or "") for q in players]
    if not all(ids) or len(ids) != len(set(ids)):
        return "Ungültige Spielerliste / Invalid roster"
    target = next(
        (q for q in players if str(q.get("player_id")) == p["target_id"]), None
    )
    reporter = next(
        (q for q in players if str(q.get("player_id")) == i.reporter_id), None
    )
    from rcon.admin_incidents import _normalize_team

    if (
        not target
        or not reporter
        or target.get("online") is False
        or reporter.get("online") is False
        or _normalize_team(target.get("team")) != p["target"]["team"]
        or _normalize_team(reporter.get("team"))
        != p.get("reporter_team", p["target"]["team"])
    ):
        return "Spieler offline oder Team geändert / Player offline or team changed"
    if p["rule"] == "communication" and (
        identity(target) != p["target"]["seat"]
        or not unique_seat(players, p["target"]["seat"])
    ):
        return "Führungsrolle geändert / Leadership seat changed"
    for pid, token in (
        (p["target_id"], p["session"]),
        (i.reporter_id, p["reporter_session"]),
    ):
        if session_token(sess, i.server_number, pid, now) != token:
            return "Sitzung geändert / Session changed"
    if not votes.discord_ready(sess):
        return "Discord nicht bereit / Discord unavailable"
    return None


def cancel_incident(sess, incident, actor):
    for event in incident.events:
        if (
            event.event_type != "report_admin"
            or event.payload.get("status") not in OPEN
        ):
            continue
        if event.payload["status"] == "sending":
            from rcon.admin_incidents import IncidentConflict

            raise IncidentConflict("Report-admin kick in progress; wait for its result")
        publish(sess, event, "manual", "Admin übernimmt / Admin takeover")


def cancel_player(sess, server, pid=None):
    for event in pending(sess, server):
        if pid is None or event.payload.get("target_id") == str(pid):
            cancel_incident(sess, event.incident, "admin")


def recover(server):
    with enter_session() as sess:
        votes.lock(sess, server)
        # Retire the old feature even when Report Admin itself is disabled.
        # Keep historical records, cancel unsent messages, never resume a kick.
        from rcon.leadership_vote.domain import OPEN as VOTE_OPEN

        for vote in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server,
                LeadershipVote.status.in_(VOTE_OPEN),
            )
        ):
            uncertain = (
                vote.payload.get("execution", {}).get("send_started_at") is not None
            )
            vote.status = "unknown" if uncertain else "cancelled"
            vote.slot, vote.ended_at = None, time.time()
            vote.payload = {
                **vote.payload,
                "result": "Führungsabstimmung eingestellt; Admins prüfen / Leadership voting retired; admins review",
            }
            votes.publish(sess, vote, vote.status, ACTOR)
        for message in sess.scalars(
            select(LeadershipMessage).where(
                LeadershipMessage.server_number == server,
                LeadershipMessage.status.in_({"pending", "sending"}),
            )
        ):
            message.status = "unknown" if message.status == "sending" else "cancelled"
        old_config = sess.scalar(
            select(UserConfig).where(UserConfig.key == votes.config_key(server))
        )
        if old_config and old_config.value.get("enabled"):
            old_config.value = {**old_config.value, "enabled": False}
        for event in pending(sess, server):
            publish(
                sess,
                event,
                "unknown" if event.payload["status"] == "sending" else "manual",
                "Dienst neu gestartet; keine Wiederholung / Service restarted; no retry",
            )
    _invalidate_user_config_cache(votes.config_key(server))


def notify_reporter(api, server, event_id, *, review=False):
    """One private receipt after a durably confirmed kick; never a warning.

    A committed send marker prevents replay. Notification failures cannot undo
    the kick receipt or schedule a second kick. Self-reporters are already gone.
    """
    field = "review_notification" if review else "reporter_notification"
    expected = "queued" if review else "kicked"
    with enter_session() as sess:
        votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        if (
            not event
            or event.incident.server_number != server
            or event.payload.get("status") != expected
            or event.payload.get(field)
            or (
                review
                and (
                    event.payload.get("rule") != "cheating"
                    or not delivered(sess, event.incident_id)
                )
            )
        ):
            return
        if event.incident.reporter_id == event.payload["target_id"]:
            event.payload = {
                **event.payload,
                field: {"status": "skipped", "reason": "self_report"},
            }
            return
    context = read_context(api)
    with enter_session() as sess:
        votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        if event.payload.get("status") != expected or event.payload.get(field):
            return
        i, p = event.incident, event.payload
        matches = [
            q
            for q in (context or {}).get("players", [])
            if str(q.get("player_id")) == i.reporter_id
        ]
        from rcon.admin_incidents import _normalize_team

        if (
            not valid_context(context, time.time())
            or context["round_id"] != p["round_id"]
            or len(matches) != 1
            or matches[0].get("online") is False
            or _normalize_team(matches[0].get("team"))
            != p.get("reporter_team", p["target"]["team"])
            or session_token(sess, server, i.reporter_id, time.time())
            != p["reporter_session"]
            or (review and invalid_reason(sess, event, context, time.time()))
        ):
            event.payload = {
                **p,
                field: {
                    "status": "skipped",
                    "reason": "reporter_unavailable_or_context_changed",
                },
            }
            return
        recipient, recipient_name = i.reporter_id, i.reporter_name
        target_name = " ".join(str(p["target_name"]).split())[:100]
        body = (
            f"Deine Meldung wurde bearbeitet: {target_name} wurde vom Server gekickt.\n"
            f"Your report was handled: {target_name} was kicked from the server."
        )
        if review:
            body = (
                f"Deine Cheatmeldung zu {target_name} ist eingegangen. Die Daten werden geprüft; Admins entscheiden über Maßnahmen.\n"
                f"Your cheat report about {target_name} was received. Evidence is being reviewed; admins decide on any action."
            )
        event.payload = {
            **p,
            field: {
                "status": "sending",
                "started_at": time.time(),
                "message": body,
            },
        }
    sent = False
    try:
        with api.without_retries():
            # The incident journal is the audit trail. Do not create a player
            # warning/action record for this informational acknowledgement.
            sent = (
                api.message_player(
                    recipient,
                    body,
                    by=ACTOR,
                    save_message=False,
                    player_name=recipient_name,
                )
                is True
            )
    except Exception:
        logger.exception("Report-admin reporter receipt uncertain; no retry")
    with enter_session() as sess:
        votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        event.payload = {
            **event.payload,
            field: {
                **event.payload[field],
                "status": "sent" if sent else "unknown",
                "finished_at": time.time(),
            },
        }


def tick(api, server):
    with enter_session() as sess:
        cfg = config(sess, server)
        tasks = [e.id for e in pending(sess, server, limit=4, due_at=time.time())]
    if not tasks:
        return
    context = read_context(api) if cfg.enabled else None
    for event_id in tasks:
        live = None
        with enter_session() as sess:
            event = sess.get(AdminIncidentEvent, event_id)
            rule = event.payload.get("rule") if event else None
            safe = (
                event
                and not invalid_reason(sess, event, context, time.time())
                and delivered(sess, event.incident_id)
            )
        if safe and rule != "communication":
            if rule == "cheating":
                try:
                    notify_reporter(api, server, event_id, review=True)
                except Exception:
                    logger.exception(
                        "Report-admin review acknowledgement unavailable; no retry"
                    )
            try:
                live = evidence_rules.fresh_logs(api)
            except Exception:
                logger.exception(
                    "Report-admin live evidence unavailable; no automatic TK sanction"
                )
        with enter_session() as sess:
            votes.lock(sess, server)
            event = sess.get(AdminIncidentEvent, event_id)
            if not event or event.payload["status"] not in {"queued", "waiting"}:
                continue
            if reason := invalid_reason(sess, event, context, time.time()):
                publish(sess, event, "manual", reason)
                continue
            if not delivered(sess, event.incident_id):
                continue
            p = event.payload
            evidence = {}
            if p["rule"] != "communication":
                status, reason, evidence = assess(
                    sess, server, event, live, time.time()
                )
                if status != "eligible":
                    publish(sess, event, status, reason, **evidence)
                    event.payload = {
                        **event.payload,
                        "incident_revision": event.incident.revision,
                    }
                    continue
            if p["mode"] == "dry_run":
                publish(
                    sess,
                    event,
                    "dry_run",
                    "Probelauf: würde kicken; kein Kick / Dry run: would kick; no kick",
                    **evidence,
                )
                continue
            # Rate limit against report spam / duplicate cases for the same session.
            previous = sess.scalar(
                select(AdminIncidentEvent.id)
                .join(AdminIncident)
                .where(
                    AdminIncident.server_number == server,
                    AdminIncidentEvent.event_type == "report_admin",
                    AdminIncidentEvent.id != event.id,
                    AdminIncidentEvent.payload["target_id"].as_string()
                    == p["target_id"],
                    AdminIncidentEvent.payload["status"]
                    .as_string()
                    .in_({"sending", "kicked", "unknown"}),
                    AdminIncidentEvent.created_at >= utc(time.time() - 300),
                )
                .limit(1)
            )
            if previous is not None:
                publish(
                    sess,
                    event,
                    "manual",
                    "Kürzlicher Eingriff; manuell prüfen / Recent action; manual review",
                )
                continue
            # Commit the durable no-retry marker BEFORE touching RCON.
            publish(
                sess, event, "sending", "Kick reserviert / Kick reserved", **evidence
            )
            event.payload = {
                **event.payload,
                "incident_revision": event.incident.revision,
            }
        # Re-read config, identity, round, and ownership after the durable commit.
        fresh = read_context(api)
        if rule == "teamkills":
            # Catch a last-moment apology, new TK or reporter retaliation before
            # the one allowed action. Read errors leave the reserved case manual.
            try:
                live = evidence_rules.fresh_logs(api)
            except Exception:
                live = None
                logger.exception("Report-admin final evidence refresh failed")
        with enter_session() as sess:
            votes.lock(sess, server)
            event = sess.get(AdminIncidentEvent, event_id)
            if event.payload["status"] != "sending":
                continue
            if reason := invalid_reason(sess, event, fresh, time.time()):
                publish(sess, event, "manual", reason)
                continue
            p = event.payload
            if p["rule"] != "communication":
                status, reason, evidence = assess(
                    sess, server, event, live, time.time()
                )
                if status != "eligible" or p["rule"] != "teamkills":
                    publish(sess, event, "manual", reason, **evidence)
                    continue
                event.payload = {**p, **evidence}
                p = event.payload
            reason = kick_reason(sess, p)
            confirmed = False
            try:
                # Same lock as manual report actions/config updates. No retries,
                # no offline==success inference, no warning or ban fallback.
                with api.without_retries(), votes.automatic_action():
                    confirmed = (
                        api.kick(
                            p["target_id"],
                            reason,
                            by=ACTOR,
                            player_name=p["target_name"],
                        )
                        is True
                    )
            except Exception:
                logger.exception(
                    "Report-admin kick result uncertain; no automatic retry"
                )
            publish(
                sess,
                event,
                "kicked" if confirmed else "unknown",
                (
                    "Kick bestätigt / Kick confirmed"
                    if confirmed
                    else "Kick unklar; Admins prüfen, keine Wiederholung / Kick uncertain; admins review, no retry"
                ),
                sent_reason=reason,
            )
        # This runs only AFTER the kick result transaction committed. Never
        # infer success from a disconnect or a failed/unconfirmed kick response.
        if confirmed:
            try:
                notify_reporter(api, server, event_id)
            except Exception:
                logger.exception(
                    "Report-admin reporter receipt failed; kick result preserved"
                )


class Runtime:
    """Single owner per server, isolated from ordinary chat/Discord processing."""

    def __init__(self):
        from rcon.utils import get_server_number

        self.server = int(get_server_number())
        self.owner = None

    def step(self, api):
        try:
            if self.owner is None:
                with enter_session() as sess:
                    engine = sess.bind
                self.owner = engine.connect()
                if self.owner.dialect.name == "postgresql":
                    acquired = self.owner.scalar(
                        text("SELECT pg_try_advisory_lock(194879, :server)"),
                        {"server": self.server},
                    )
                    self.owner.commit()
                    if not acquired:
                        self.close()
                        return
                recover(self.server)
            self.owner.execute(text("SELECT 1"))
            self.owner.commit()
            tick(api, self.server)
        except Exception:
            logger.exception(
                "Report-admin unavailable; reports remain for manual review"
            )
            self.close()

    def close(self):
        owner, self.owner = self.owner, None
        if owner is not None:
            try:
                if owner.dialect.name == "postgresql" and not owner.invalidated:
                    owner.rollback()
                    owner.execute(
                        text("SELECT pg_advisory_unlock(194879, :server)"),
                        {"server": self.server},
                    )
                    owner.commit()
            except Exception:
                owner.invalidate()
            finally:
                owner.close()
