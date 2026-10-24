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


def target(
    incident, players, decision, allow_self_reports, communication_squad_members=False
):
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
        communication_squad_members=communication_squad_members
        and d.target_kind == "player",
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
    decision = before = after = None
    failure = None
    try:
        decision = ReportReasonDecision.model_validate(assessment.get("decision"))
        before = target(
            i.to_dict(),
            request["roster"],
            decision,
            cfg.allow_self_reports,
            cfg.communication_squad_members,
        )
        after = target(
            i.to_dict(),
            context["players"],
            decision,
            cfg.allow_self_reports,
            cfg.communication_squad_members,
        )
    except (ValueError, TypeError, KeyError):
        failure = "invalid_interpretation_or_roster"
    summary = {
        "decision": decision.model_dump() if decision else None,
        "model": str(assessment.get("model") or "")[:100],
        "prompt_version": str(assessment.get("prompt_version") or "")[:64],
    }
    if not failure:
        if not before:
            failure = "original_target_unresolved"
        elif not after:
            failure = "live_target_unresolved"
        elif before != after:
            failure = "target_identity_changed"
        elif not getattr(cfg, decision.rule, False):
            failure = "rule_disabled"
    if failure:
        summary["target_check"] = target_check(
            i,
            request.get("roster"),
            context["players"],
            before,
            after,
            failure,
            cfg.communication_squad_members,
        )
    event.payload = {**p, "reason_analysis": summary}
    if failure:
        reasons = {
            "invalid_interpretation_or_roster": "KI-Antwort oder Spielerdaten ungültig / Invalid AI response or player data",
            "original_target_unresolved": "Ziel in der ursprünglichen Meldung nicht sicher zugeordnet / Target not safely identified in original report",
            "live_target_unresolved": "Ziel oder Melder erfüllt die aktuellen Spieler- und Teamprüfungen nicht / Target or reporter no longer passes current player and team checks",
            "target_identity_changed": "Spieleridentität, Team oder Position während der KI-Prüfung geändert / Player identity, team or position changed during AI review",
            "rule_disabled": "Diese automatische Maßnahme ist deaktiviert / This automatic action is disabled",
        }
        admin.publish(
            sess,
            event,
            "manual",
            reasons[failure],
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


def target_check(incident, original, current, before, after, failure, allow_members):
    """Bounded audit evidence, not authority to bypass a failed target check.

    Retain only the relevant participants and seat counts, never a full second
    roster, secrets, exception text or model-controlled identifiers. This also
    distinguishes a valid AI classification from failed live identity checks.
    """
    from rcon.report_admin_rules import communication_identity
    from rcon.admin_incidents import _normalize_team

    pid = (before or after or {}).get("player_id") or incident.target_id

    def snapshot(players):
        if not isinstance(players, list):
            return {"invalid_roster": True}
        rows = [p for p in players if isinstance(p, dict)]
        ids = [str(p.get("player_id") or "") for p in rows]

        def participant(player_id):
            matches = [p for p in rows if str(p.get("player_id")) == player_id]
            if len(matches) != 1:
                return {"matches": len(matches)}
            p = matches[0]
            seat = communication_identity(p, allow_members)
            # All these fields come from the roster, never AI-generated IDs.
            return {
                "matches": 1,
                "online": p.get("online") is not False,
                "team": _normalize_team(p.get("team")),
                "role": str(p.get("role") or "")[:100],
                "squad": str(p.get("unit_name") or "")[:100],
                "squad_id": str(p.get("unit_id") or "")[:100],
                "seat": seat,
                "same_seat_count": (
                    sum(
                        all(
                            other.get(k) == seat.get(k)
                            for k in ("team", "kind", "squad_id")
                        )
                        for q in rows
                        if seat and (other := communication_identity(q, allow_members))
                    )
                    if seat and seat["kind"] != "squadmember"
                    else None
                ),
            }

        return {
            "missing_ids": sum(not value for value in ids),
            "duplicate_ids": len(ids) - len(set(ids)),
            "target": participant(pid) if pid else None,
            "reporter": participant(incident.reporter_id),
        }

    return {
        "code": failure,
        "before_resolved": bool(before),
        "after_resolved": bool(after),
        "changed_fields": [
            k
            for k in ("player_id", "name", "team", "seat")
            if before and after and before.get(k) != after.get(k)
        ],
        "original": snapshot(original),
        "current": snapshot(current),
    }
