"""Persist AI interpretation separately from deterministic moderation authority."""

import re

from rcon.report_reason_contract import ReportReasonDecision


def enqueue(sess, incident, context, now, cfg):
    from rcon import report_admin as admin
    from rcon.models import AdminIncidentEvent

    raw = str(incident.raw_message or "")
    if incident.source != "chat" or not re.match(r"^\s*!admin\b", raw, re.I):
        return True
    event = AdminIncidentEvent(
        actor=admin.ACTOR,
        event_type="report_admin",
        idempotency_key=f"report-admin:{incident.id}",
        created_at=admin.utc(now),
        payload={
            "status": "manual",
            "mode": cfg.mode,
            "rule": "pending",
            "result": "KI-Einordnung nicht möglich / AI interpretation unavailable",
            "updated_at": now,
        },
    )
    incident.events.append(event)
    stamp = (context or {}).get("event_time")
    if (
        len(raw) > 4000
        or not admin.valid_context(context, now)
        or not isinstance(stamp, (int, float))
        or not 0 <= now - stamp <= 30
        or not 1 <= len(context["players"]) <= 150
        or not admin.votes.discord_ready(sess)
    ):
        return True
    players = context["players"]
    ids = [str(p.get("player_id") or "") for p in players]
    if not all(ids) or len(ids) != len(set(ids)):
        return True
    reporter = next(
        (p for p in players if str(p["player_id"]) == incident.reporter_id), None
    )
    token = admin.session_token(
        sess, incident.server_number, incident.reporter_id, stamp
    )
    if not reporter or reporter.get("online") is False or token is None:
        return True
    roster = [
        {
            k: p[k]
            for k in (
                "player_id",
                "name",
                "player_name",
                "team",
                "role",
                "unit_name",
                "unit_id",
                "online",
            )
            if k in p
        }
        for p in players
    ]
    event.payload = {
        **event.payload,
        "status": "classifying",
        "result": "Vollständiger Meldegrund wird eingeordnet / Interpreting the complete report",
        "config": cfg.model_dump(),
        "report_time": stamp,
        "round_id": context["round_id"],
        "round_start": context["round_start"],
        "reporter_session": token,
        "reporter_team": admin._normalize_team(reporter.get("team")),
        "incident_revision": incident.revision,
        "original_target_id": incident.target_id,
        "original_message": raw,
        "reason_request": {"status": "pending", "roster": roster},
    }
    return True


def invalid_request(sess, event, now):
    from rcon import report_admin as admin

    p, i = event.payload, event.incident
    cfg = admin.config(sess, i.server_number)
    if (
        not cfg.enabled
        or cfg.reason_mode != "ai"
        or cfg.model_dump() != p.get("config")
    ):
        return "Einstellungen geändert / Settings changed"
    if (
        i.status != "new"
        or i.assigned_to
        or i.revision != p.get("incident_revision")
        or i.target_id != p.get("original_target_id")
        or i.raw_message != p.get("original_message")
    ):
        return (
            "Admin-Bearbeitung oder Meldung geändert / Admin handling or report changed"
        )
    if not 0 <= now - p.get("report_time", 0) <= admin.MAX_REPORT_AGE:
        return "KI-Einordnung abgelaufen / AI interpretation expired"
    return None


def target(incident, players, decision, allow_self_reports):
    from rcon.admin_incidents import parse_chat_report
    from rcon.report_admin_rules import (
        target_for,
        exact_player,
        conservative_name_match,
    )

    d = ReportReasonDecision.model_validate(decision)
    raw = str(incident.get("raw_message") or "")
    body = re.sub(r"^\s*!admin\b", "", raw, count=1, flags=re.I)
    if (
        d.rule == "manual"
        or not d.unambiguous
        or d.uncertainties
        or d.target_kind == "none"
        or not d.target_text.strip()
        or not d.allegation_excerpt.strip()
        or d.target_text not in body
        or d.allegation_excerpt not in body
        or "!admin" in d.target_text.casefold()
        or d.allegation_excerpt.strip() == d.target_text.strip()
        or (d.rule != "communication" and d.target_kind != "player")
    ):
        return None
    # The model extracts a reference, never supplies an executable player ID.
    # Reuse the independent exact/typo/leadership resolver on that reference.
    reporter = next(
        (p for p in players if str(p.get("player_id")) == incident.get("reporter_id")),
        {},
    )
    message = "!admin " + d.target_text
    parsed = parse_chat_report(
        message,
        current_players=players,
        reporter_context=reporter,
        fuzzy_threshold=0.70,
        context_mode="enabled",
    )
    if not parsed:
        return None
    named_player = None
    if d.target_kind == "player":
        named_player = exact_player(
            parsed["subjects"], players
        ) or conservative_name_match(parsed["subjects"], players)
        if not named_player:
            return None  # A missing named player must not become a squad's leader.
    found = target_for(
        {**incident, "raw_message": message, "subjects": parsed["subjects"]},
        players,
        d.rule,
        allow_self_reports=allow_self_reports,
    )
    if not found or (
        named_player and found["player_id"] != str(named_player["player_id"])
    ):
        # A valid player-name typo must never be redirected to the leader of a
        # similarly named squad. Squad precedence applies only to squad reports.
        return None
    seat_kind = (found.get("seat") or {}).get("kind")
    if (d.target_kind == "commander" and seat_kind != "commander") or (
        d.target_kind == "squad" and seat_kind != "squadleader"
    ):
        return None
    # Never override an explicit admin rejection or another confirmed player.
    if any(
        s.get("state") == "rejected"
        or (
            s.get("state") == "confirmed"
            and (s.get("player_id") or s.get("leader_player_id"))
            and str(s.get("player_id") or s.get("leader_player_id"))
            != found["player_id"]
        )
        for s in incident.get("subjects", [])
    ):
        return None
    return found


def finish(sess, event, context, now):
    """Called under the same server action lock; never calls an external model."""
    from rcon import report_admin as admin

    p, i = event.payload, event.incident
    if problem := invalid_request(sess, event, now):
        admin.publish(sess, event, "manual", problem)
        return
    if not admin.valid_context(context, now) or context["round_id"] != p["round_id"]:
        admin.publish(
            sess,
            event,
            "manual",
            "Veraltete Daten oder Kartenwechsel / Stale data or map changed",
        )
        return
    request = p["reason_request"]
    if request["status"] in {"pending", "sending"}:
        return
    assessment = request.get("analysis") or {}
    if request["status"] != "done":
        admin.publish(
            sess,
            event,
            "manual",
            (
                "KI-Zeitlimit überschritten; manuelle Prüfung / AI timed out; manual review"
                if request.get("failure_code") == "timeout"
                else "KI nicht verfügbar; kein Regel-Fallback / AI unavailable; no keyword fallback"
            ),
        )
        return
    cfg = admin.config(sess, i.server_number)
    try:
        decision = ReportReasonDecision.model_validate(assessment.get("decision"))
        before = target(
            i.to_dict(), request["roster"], decision, cfg.allow_self_reports
        )
        after = target(
            i.to_dict(), context["players"], decision, cfg.allow_self_reports
        )
    except (ValueError, TypeError, KeyError):
        decision = before = after = None
    summary = {
        "decision": decision.model_dump() if decision else None,
        "model": str(assessment.get("model") or "")[:100],
        "prompt_version": str(assessment.get("prompt_version") or "")[:64],
    }
    event.payload = {**p, "reason_analysis": summary}
    if not before or before != after or not getattr(cfg, decision.rule, False):
        admin.publish(
            sess,
            event,
            "manual",
            "KI-Einordnung oder Spielerzuordnung nicht eindeutig / AI interpretation or player match unclear",
        )
        return
    intervention = p.get("player_interventions", {}).get(after["player_id"])
    if intervention:
        admin.publish(
            sess,
            event,
            "manual",
            "Maßnahme gegen Zielspieler während KI-Prüfung / Target intervention during AI review",
            intervention_actor=intervention["actor"],
        )
        return
    if (
        admin.session_token(sess, i.server_number, i.reporter_id, now)
        != p["reporter_session"]
        or admin._normalize_team(
            next(
                (
                    q.get("team")
                    for q in context["players"]
                    if str(q.get("player_id")) == i.reporter_id
                ),
                None,
            )
        )
        != p["reporter_team"]
    ):
        admin.publish(
            sess,
            event,
            "manual",
            "Melder-Sitzung oder Team geändert / Reporter session or team changed",
        )
        return
    # Bind to the original event time, never to a reconnect/new incumbent after
    # model latency. enqueue also checks both current database session tokens.
    admin.enqueue(
        sess,
        i,
        {**context, "event_time": p["report_time"]},
        now,
        interpreted=(decision.rule, after),
        existing_event=event,
    )
    event.payload = {**event.payload, "reason_analysis": summary}
    admin.publish(sess, event, event.payload["status"], event.payload["result"])
    event.payload = {**event.payload, "incident_revision": i.revision}
