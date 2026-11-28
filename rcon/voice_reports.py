"""Player-confirmed voice reports in the existing per-server incident journal."""

import os
import re
import time

from sqlalchemy import select

from rcon import report_admin as admin
from rcon.admin_incidents import _normalize_team
from rcon.models import AdminIncident, AdminIncidentEvent
from rcon.report_admin_rules import communication_identity, unique_communication_seat


from rcon.voice_language_text import BUILTIN, TEXT

_REPLIES = {
    locale: (yes.casefold(), no.casefold())
    for locale, yes, no in zip(
        BUILTIN, TEXT["fixed"], TEXT["still_silent"], strict=True
    )
}
_BARE = frozenset(word for pair in _REPLIES.values() for word in pair)
KICK_PROCESSING_SECONDS = 30


def chat_candidate(message):
    text = str(message or "").strip().casefold()
    return text in _BARE or bool(re.match(r"^!voice\b", text))


def _listed(server, setting):
    return str(server) in {part.strip() for part in os.getenv(setting, "").split(",")}


def enabled(server):
    return _listed(server, "FRONTLINE_VOICE_REPORT_SERVERS")


def live_kicks_enabled(server):
    return enabled(server) and _listed(server, "FRONTLINE_VOICE_LIVE_KICK_SERVERS")


def discord_intake(incident, context):
    return bool(
        enabled(incident.server_number)
        and incident.source == "manual"
        and (context or {}).get("voice_discord_intake") is True
        and (incident.reporter_context or {}).get("voice_discord_id")
        and any(
            e.event_type == "created" and e.actor == "discord:voice-player"
            for e in incident.events
        )
    )


def named_target(player, players):
    seat = communication_identity(player, True)
    if seat and unique_communication_seat(players, seat):
        return {
            "player_id": str(player["player_id"]),
            "name": str(player.get("name") or player.get("player_name") or ""),
            "team": seat["team"],
            "seat": seat,
        }
    return None


def max_age(payload):
    voice = payload["voice"]
    # No extension to the original 60-second validity window before dispatch.
    if voice["phase"] == "clarify":
        return 120
    sent_at = voice.get("notice_sent_at")
    if sent_at is None:
        return 60
    if voice["phase"] == "kick_ready":
        # Anchor dispatch to the accepted reply, including across worker ticks.
        answered_at = voice.get("answer_at")
        if answered_at is None:
            return -1
        return answered_at + KICK_PROCESSING_SECONDS - payload["report_time"]
    # A witness with an existing prompt can receive the next one after its window.
    horizon = max(
        sent_at + 180,
        voice.get("deadline", 0),
        (
            payload.get("ready_at", 0) + 15
            if voice["phase"] in {"notice_sent", "question_sending"}
            else 0
        ),
    )
    return horizon - payload["report_time"]


def _reporter_language(sess, incident, players):
    from rcon.voice_language import report_language

    context = incident.reporter_context or {}
    if incident.source == "manual" and context.get("voice_locale"):
        from rcon.voice_language import normalize_language

        locale = normalize_language(context["voice_locale"])
        if locale:
            return locale
    return report_language(
        sess,
        incident.raw_message or incident.reason,
        game_id=incident.reporter_id,
        discord_id=context.get("voice_discord_id"),
        handles=[p.get("name") or p.get("player_name") or "" for p in players],
    )


def _replace(event, **values):
    event.payload = {**event.payload, "voice": {**event.payload["voice"], **values}}


def _message(sess, event, key, recipient, token, *, locale):
    if not recipient or token is None:
        return
    job = AdminIncidentEvent(
        actor=admin.ACTOR,
        event_type="voice_game_message",
        idempotency_key=f"voice:{event.incident_id}:{key}",
        created_at=admin.utc(time.time()),
        payload={
            "status": "pending",
            "key": key,
            "recipient": recipient,
            "session": token,
            "locale": locale,
            "event_id": event.id,
            "expires": time.time() + 120,
        },
    )
    event.incident.events.append(job)


def _reporter_message(sess, event, key):
    i, p = event.incident, event.payload
    if i.source == "chat":
        _message(
            sess,
            event,
            key,
            i.reporter_id,
            p.get("reporter_session"),
            locale=p["voice"]["reporter_language"],
        )


def _change(sess, event, phase, *, due=0, **meta):
    _replace(event, phase=phase, **meta)
    event.payload = {**event.payload, "ready_at": due}
    admin.publish(sess, event, "voice", phase)
    event.payload = {**event.payload, "incident_revision": event.incident.revision}


def _final(sess, event, phase, key, reason):
    _replace(event, phase=phase, message_key=key)
    admin.publish(sess, event, "resolved" if phase == "resolved" else "manual", reason)


def on_publish(sess, event, status, now):
    """All terminal paths, including admin takeover, recovery and unknown results."""
    if status not in {"manual", "unknown", "kicked", "resolved", "dry_run"}:
        return
    voice = event.payload["voice"]
    if voice.get("finished_at"):
        return
    phase = voice["phase"] if voice["phase"] == "duplicate" else status
    key = (
        voice.get("message_key")
        or ("notice_failed" if voice["phase"] == "notice_sending" else None)
        or {
            "kicked": "kicked",
            "unknown": "unconfirmed",
            "dry_run": "dry_run",
            "resolved": "resolved",
        }.get(status, "manual")
    )
    _replace(event, phase=phase, message_key=key, finished_at=now)
    if phase == "resolved":
        i = event.incident
        i.status, i.assigned_to, i.resolved_at = "resolved", admin.ACTOR, admin.utc(now)
    _reporter_message(sess, event, key)
    from rcon.voice_player_delivery import queue_update

    queue_update(sess, event, "final")


def clarify(sess, event, players, now, context=None):
    """Keep a PC case open for one explicit correction by its original reporter."""
    i = event.incident
    sess.flush()
    if i.source != "chat" or event.payload.get("clarified"):
        admin.publish(
            sess, event, "manual", "Target unclear after clarification; admin review"
        )
        return
    cfg = admin.config(sess, i.server_number)
    v = {
        "phase": "clarify",
        "reporter_language": _reporter_language(sess, i, players),
        "seats": {
            str(p["player_id"]): communication_identity(p, True)
            for p in players
            if p.get("player_id")
        },
    }
    event.payload = {
        **event.payload,
        "voice": v,
        "config": cfg.model_dump(),
        "reporter_session": admin.session_token(
            sess, i.server_number, i.reporter_id, now
        ),
        "report_time": event.payload.get(
            "report_time", (context or {}).get("event_time", now)
        ),
        "round_id": event.payload.get("round_id", (context or {}).get("round_id")),
        "voice_pilot": True,
    }
    _change(sess, event, "clarify", due=now + 120, deadline=now + 120)
    _reporter_message(sess, event, "clarify")


def clarify_target(server, event_id, pid, name, context, stamp):
    from rcon import report_reason
    from rcon.admin_incidents import player_snapshot, _subject_from_payload

    now = time.time()
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        if not event or event.event_type != "report_admin":
            return False
        i, p = event.incident, event.payload
        v = p.get("voice", {})
        if not (
            i.server_number == server
            and i.source == "chat"
            and i.reporter_id == pid
            and p.get("status") == "voice"
            and v.get("phase") == "clarify"
            and i.status == "new"
            and not i.assigned_to
            and i.revision == p["incident_revision"]
            and p["report_time"] <= stamp <= now < v["deadline"]
            and admin.valid_context(context, now)
            and context["round_id"] == p["round_id"]
            and p.get("reporter_session")
            and admin.session_token(sess, server, pid, now) == p["reporter_session"]
        ):
            return False
        cfg = admin.config(sess, server)
        if cfg.model_dump() != p["config"] or not cfg.enabled or not enabled(server):
            return False
        matches = [
            row
            for row in context["players"]
            if str(row.get("name") or row.get("player_name") or "").casefold()
            == name.strip().casefold()
        ]
        if len(matches) != 1:
            return False
        row = matches[0]
        target = named_target(row, context["players"])
        if (
            not target
            or target["player_id"] == pid
            or v["seats"].get(target["player_id"]) != target["seat"]
            or not admin.session_token(
                sess, server, target["player_id"], p["report_time"]
            )
        ):
            return False
        original = i.raw_message
        clarified = f"{original} (Target: {target['name']})"
        if len(clarified) > 4000:
            return False
        # Retain the original words in the journal; a name is never evidence of misconduct.
        i.events.append(
            AdminIncidentEvent(
                actor="system:voice-clarification",
                event_type="voice_target_clarified",
                payload={"original": original, "target_id": target["player_id"]},
                created_at=admin.utc(now),
            )
        )
        i.raw_message = clarified
        for subject in i.subjects:
            subject.is_primary = False
        i.subjects.append(
            _subject_from_payload(
                {
                    "kind": "player",
                    "state": "confirmed",
                    "is_primary": True,
                    "player_id": target["player_id"],
                    "display_name": target["name"],
                    "team": target["team"],
                    "match_method": "name_contained",
                    "snapshot": player_snapshot(row),
                },
                actor=admin.ACTOR,
            )
        )
        i.target_id, i.target_name = target["player_id"], target["name"]
        i.revision += 1
        for_request = {**context, "event_time": stamp}
        if cfg.reason_mode == "ai":
            report_reason.enqueue(sess, i, for_request, now, cfg, existing_event=event)
            event.payload = {**event.payload, "clarified": True}
        else:
            admin.enqueue(
                sess,
                i,
                for_request,
                now,
                interpreted=("communication", target),
                existing_event=event,
            )
        return True


def _channel(witness, target):
    seat = communication_identity(witness, True)
    if not seat or not target or seat["team"] != target["team"]:
        return None
    if seat.get("squad_id") and seat["squad_id"] == target.get("squad_id"):
        return "squad"
    if all(s["kind"] in {"commander", "squadleader"} for s in (seat, target)):
        return "command"
    return None


def begin(sess, event, players, now):
    i, p = event.incident, event.payload
    sess.flush()
    event.payload = {
        **p,
        "mode": p["mode"] if live_kicks_enabled(i.server_number) else "dry_run",
        "voice": {
            "phase": "notice_pending",
            "reporter_language": _reporter_language(sess, i, players),
        },
    }
    # The server lock held by enqueue also serializes separate reporters and Discord imports.
    previous = sess.scalars(
        select(AdminIncidentEvent)
        .join(AdminIncident)
        .where(
            AdminIncident.server_number == i.server_number,
            AdminIncidentEvent.event_type == "report_admin",
            AdminIncidentEvent.id != event.id,
            AdminIncidentEvent.payload["target_id"].as_string() == p["target_id"],
            AdminIncidentEvent.payload["voice"]["phase"].as_string().is_not(None),
            AdminIncidentEvent.payload["round_id"].as_string() == p["round_id"],
            AdminIncidentEvent.payload["session"].as_integer() == p["session"],
            AdminIncidentEvent.created_at >= admin.utc(now - 300),
        )
    ).all()
    if any(
        e.payload["voice"]["phase"] not in {"duplicate", "clarify"} for e in previous
    ):
        _final(
            sess,
            event,
            "duplicate",
            "duplicate",
            "Another voice report already covers this player and session",
        )
        return
    from rcon.voice_language import VoiceVerifiedIdentity

    ids = [str(row["player_id"]) for row in players if row.get("player_id")]
    linked_ids = set(
        sess.scalars(
            select(VoiceVerifiedIdentity.game_id).where(
                VoiceVerifiedIdentity.game_id.in_(ids)
            )
        )
    )
    candidates = []
    for player in players:
        pid = str(player.get("player_id") or "")
        channel = _channel(player, p["target"]["seat"])
        if not channel or not pid or pid == p["target_id"]:
            continue
        platform = str(player.get("platform") or "").lower().split("::")[-1]
        # Existing !admin chat is positive evidence that this witness can type.
        # WinGDK alone cannot distinguish an Xbox from a Windows Store PC.
        chat_reporter = pid == i.reporter_id and i.source == "chat"
        if pid == i.reporter_id and i.source == "manual" and pid in linked_ids:
            route = "discord"
        elif chat_reporter or platform in {"steam", "egs", "epic", "windows", "pc"}:
            route = "pc"
        elif pid in linked_ids:
            route = "discord"
        else:
            continue
        candidates.append(
            (pid != i.reporter_id, channel != "squad", pid, player, channel, route)
        )
    witness_id = witness_session = witness_seat = None
    channel = "command" if p["target"]["seat"]["kind"] == "commander" else "squad"
    witness_route = None
    for _, _, pid, player, witness_channel, route in sorted(
        candidates, key=lambda c: c[:3]
    ):
        token = admin.session_token(sess, i.server_number, pid, p["report_time"])
        if token is not None:
            witness_id, witness_session, witness_seat = (
                pid,
                token,
                communication_identity(player, True),
            )
            channel = witness_channel
            witness_route = route
            break
    _replace(
        event,
        witness_id=witness_id,
        witness_session=witness_session,
        witness_seat=witness_seat,
        witness_route=witness_route,
        channel=channel,
        external=not i.reporter_id or witness_id != i.reporter_id,
    )
    event.payload = {
        **event.payload,
        "status": "voice",
        "ready_at": now,
        "result": "Voice contact notice pending",
    }
    if not live_kicks_enabled(i.server_number):
        from rcon.voice_live_test import bind

        bind(sess, event, now)


def witness_problem(sess, event, players, now):
    v = event.payload["voice"]
    if v.get("phase") == "kick_ready" and not (
        v.get("answer") == "still_silent" and v.get("answer_at") and v.get("witness_id")
    ):
        return "Voice witness response missing"
    if not v.get("witness_id"):
        return None
    w = next((p for p in players if str(p.get("player_id")) == v["witness_id"]), None)
    if (
        not w
        or communication_identity(w, True) != v["witness_seat"]
        or _channel(w, event.payload["target"]["seat"]) != v["channel"]
        or admin.session_token(sess, event.incident.server_number, v["witness_id"], now)
        != v["witness_session"]
    ):
        return "Voice witness role or session changed"
    return None


def _send(api, pid, body):
    try:
        with api.without_retries():
            return (
                api.message_player(pid, body, by=admin.ACTOR, save_message=False)
                is True
            )
    except Exception:
        admin.logger.exception("Voice message outcome unknown")
        return False


def _pc_slot(sess, event, now):
    """A simple reply must belong to just one question in this witness session."""
    voice = event.payload["voice"]
    v = AdminIncidentEvent.payload["voice"]
    previous = sess.scalars(
        select(AdminIncidentEvent)
        .join(AdminIncident)
        .where(
            AdminIncident.server_number == event.incident.server_number,
            AdminIncidentEvent.event_type == "report_admin",
            AdminIncidentEvent.id != event.id,
            AdminIncidentEvent.payload["round_id"].as_string()
            == event.payload["round_id"],
            v["witness_session"].as_integer() == voice["witness_session"],
            v["witness_id"].as_string() == voice["witness_id"],
            v["witness_route"].as_string() == "pc",
            v["question_reserved_at"].as_float().is_not(None),
        )
    ).all()
    ready = now
    for other in previous:
        prior = other.payload["voice"]
        deadline = prior.get("deadline", prior["question_reserved_at"] + 120)
        if not prior.get("answer_at") and now >= deadline:
            # A late answer to the expired question would be indistinguishable.
            # Do not ask this witness for another unnumbered reply in this round.
            return None
        ready = max(ready, deadline + 1)
    return ready


def advance(api, server, event_id, context):
    from rcon.voice_language import preferred_language, render
    from rcon.voice_player_delivery import queue_update

    now = time.time()
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        p, v = event.payload, event.payload["voice"]
        if p["status"] != "voice":
            return
        if v["phase"] == "clarify":
            if now >= v["deadline"]:
                _final(
                    sess,
                    event,
                    "manual",
                    "expired",
                    "No target clarification before deadline",
                )
            return
        if problem := admin.invalid_reason(sess, event, context, now):
            _final(sess, event, "manual", "manual", problem)
            return
        if not admin.delivered(sess, event.incident_id):
            return
        if v.get("live_test") or v.get("chat_pilot"):
            from rcon.voice_live_test import keep_or_simulate

            keep_or_simulate(sess, event, now)
            p = event.payload
        if v["phase"] == "awaiting_answer":
            if now >= v["deadline"]:
                _final(
                    sess,
                    event,
                    "manual",
                    "expired",
                    "No voice witness reply within two minutes",
                )
            return
        if v["phase"] == "notice_pending":
            sending = "notice_sending"
            recipient = p["target_id"]
            key = "notice_command" if v["channel"] == "command" else "notice_squad"
        elif v["phase"] == "notice_sent" and now >= v["notice_sent_at"] + 60:
            if not v["witness_id"]:
                _final(
                    sess, event, "manual", "manual", "No verified participant available"
                )
                return
            if v.get("witness_route") == "pc":
                ready = _pc_slot(sess, event, now)
                if ready is None or ready > v["notice_sent_at"] + 240:
                    _final(
                        sess,
                        event,
                        "manual",
                        "manual",
                        "Another voice question makes a short reply ambiguous",
                    )
                    return
                if ready > now:
                    event.payload = {**p, "ready_at": ready}
                    return
            sending = "question_sending"
            recipient = v["witness_id"]
            key = "question"
        else:
            return
        # Persist reservation independently from transport. Never repeat on restart.
        _change(
            sess,
            event,
            sending,
            # Keep the scheduled time through the final check before sending.
            due=p.get("ready_at", 0) if sending == "question_sending" else 0,
            **({"question_reserved_at": now} if sending == "question_sending" else {}),
        )
    try:
        fresh = admin.read_context(api)
    except Exception:
        fresh = None
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        p, v = event.payload, event.payload["voice"]
        if p["status"] != "voice" or v["phase"] != sending:
            return
        now = time.time()
        if problem := admin.invalid_reason(sess, event, fresh, now):
            _final(sess, event, "manual", "manual", problem)
            return
        locale = (
            v["reporter_language"]
            if sending == "question_sending" and recipient == event.incident.reporter_id
            else preferred_language(sess, game_id=recipient)
        )
        discord_question = (
            sending == "question_sending" and v.get("witness_route") == "discord"
        )
        if discord_question:
            from rcon.voice_language import linked_discord_id

            if not linked_discord_id(sess, recipient):
                _final(
                    sess,
                    event,
                    "manual",
                    "manual",
                    "Witness Discord link is no longer available",
                )
                return
        else:
            body = render(
                sess, key, locale, target=p["target_name"], case=str(event.id)
            )
            if sending == "question_sending":
                hint = render(sess, "pc_reply", locale, case=str(event.id))
                if locale == "en":
                    # Keep the English prompt concise while retaining the reply
                    # words used before English became the unknown-player default.
                    hint += " Also accepted: Ja / Nein."
                body += "\n" + hint
                reply_language = (
                    ("de+en" if locale == "en" else locale)
                    if locale in _REPLIES
                    else (
                        "de+en"
                        if hint == render(sess, "pc_reply", "de+en", case=str(event.id))
                        else "en"
                    )
                )
                _replace(event, reply_language=reply_language)
    # The committed phase owns this send. Keep the game-server round trip
    # outside the transaction so an admin can take over while it is pending.
    sent = discord_question or _send(api, recipient, body)
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        if not event or event.payload["status"] != "voice":
            return
        v = event.payload["voice"]
        if v["phase"] != sending:
            return
        now = time.time()
        if sending == "notice_sending":
            if not sent:
                _final(
                    sess,
                    event,
                    "manual",
                    "notice_failed",
                    "Private notice not confirmed; administrator review",
                )
                return
            _change(sess, event, "notice_sent", due=now + 60, notice_sent_at=now)
            _reporter_message(
                sess, event, "notice_external" if v["external"] else "notice_sent"
            )
            queue_update(sess, event, "notice")
        else:
            # Verified Discord witnesses can answer privately even without game chat.
            if not discord_question and not sent:
                _final(
                    sess,
                    event,
                    "manual",
                    "manual",
                    "Witness question delivery not confirmed",
                )
                return
            deadline = now + 120
            _change(
                sess,
                event,
                "awaiting_answer",
                due=deadline,
                question_at=now,
                deadline=deadline,
            )
            queue_update(sess, event, "question")


def _open_pc_questions(sess, server, player_id, stamp, now):
    v = AdminIncidentEvent.payload["voice"]
    return sess.scalars(
        select(AdminIncidentEvent)
        .join(AdminIncident)
        .where(
            AdminIncident.server_number == server,
            AdminIncidentEvent.event_type == "report_admin",
            AdminIncidentEvent.payload["status"].as_string() == "voice",
            v["phase"].as_string() == "awaiting_answer",
            v["witness_route"].as_string() == "pc",
            v["witness_id"].as_string() == str(player_id),
            v["question_at"].as_float() <= stamp,
            v["deadline"].as_float() > now,
        )
        .limit(2)
    ).all()


def _announced(voice, word):
    locale = voice.get("reply_language")
    if not locale:
        # A case created by older software advertised only a numbered command.
        return False
    if locale == "de+en":
        return word in _REPLIES["de"] + _REPLIES["en"]
    return word in _REPLIES.get(locale, _REPLIES["en"])


def _answer(
    server, case, player_id, working, context, at, *, by_event=False, bare_word=None
):
    if not enabled(server) or type(working) is not bool or not player_id:
        return False
    now = time.time()
    stamp = now if at is None else at
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        query = (
            select(AdminIncidentEvent)
            .join(AdminIncident)
            .where(
                AdminIncident.server_number == server,
                AdminIncidentEvent.event_type == "report_admin",
            )
        )
        if case is None:
            matches = _open_pc_questions(sess, server, player_id, stamp, now)
            if len(matches) != 1:
                return False
            event = matches[0]
            if bare_word is not None and not _announced(
                event.payload["voice"], bare_word
            ):
                return False
        else:
            event = sess.scalar(
                query.where(
                    AdminIncidentEvent.id == case
                    if by_event
                    else AdminIncident.id == case
                )
            )
        if not event or event.payload["status"] != "voice":
            return False
        v = event.payload.get("voice", {})
        if (
            v.get("phase") != "awaiting_answer"
            or str(player_id) != v.get("witness_id")
            or not v["question_at"] <= stamp <= now < v["deadline"]
        ):
            return False
        if reason := admin.invalid_reason(sess, event, context, now):
            _final(sess, event, "manual", "manual", reason)
            return False
        if v.get("live_test") or v.get("chat_pilot"):
            from rcon.voice_live_test import keep_or_simulate

            keep_or_simulate(sess, event, now)
        _replace(event, answer_at=now, answer="working" if working else "still_silent")
        if working:
            _final(
                sess,
                event,
                "resolved",
                "resolved",
                "Witness confirmed communication restored",
            )
        else:
            _replace(event, phase="kick_ready")
            admin.publish(
                sess,
                event,
                "queued",
                "Verified witness confirms communication still unavailable",
            )
            event.payload = {
                **event.payload,
                "incident_revision": event.incident.revision,
            }
        return True


def answer(server, case_id, player_id, working, context, *, at=None):
    return _answer(server, case_id, player_id, working, context, at)


def handle_chat(api, log, server):
    text = str(log.get("sub_content") or "").strip()
    word = text.casefold()
    if not enabled(server):
        return False
    if word in _BARE:
        from rcon.leadership_vote.domain import event_time

        stamp = event_time(log)
        pid = str(log.get("player_id_1") or "")
        now = time.time()
        if stamp is None or not pid or stamp > now:
            return False
        try:
            # A normal yes/no in team chat does not trigger a live server request.
            with admin.enter_session() as sess:
                matches = _open_pc_questions(sess, server, pid, stamp, now)
                if len(matches) != 1 or not _announced(
                    matches[0].payload["voice"], word
                ):
                    return False
            return _answer(
                server,
                None,
                pid,
                any(word == yes for yes, _ in _REPLIES.values()),
                admin.read_context(api),
                stamp,
                bare_word=word,
            )
        except Exception:
            admin.logger.exception(
                "Voice reply unavailable; ordinary chat flow continues"
            )
            return False
    if not re.match(r"^!voice\b", text, re.I):
        return False
    short = re.fullmatch(r"!voice\s+(ja|nein|yes|no|oui|non|tak|nie|nee)", text, re.I)
    if short:
        from rcon.leadership_vote.domain import event_time

        stamp = event_time(log)
        if stamp is not None:
            _answer(
                server,
                None,
                str(log.get("player_id_1") or ""),
                short[1].lower() in {"ja", "yes", "oui", "tak"},
                admin.read_context(api),
                stamp,
            )
        return True
    clarification = re.fullmatch(
        r"!voice\s+([1-9][0-9]{0,17})\s+target\s+([^\r\n]{1,255})", text, re.I
    )
    if clarification:
        from rcon.leadership_vote.domain import event_time

        stamp = event_time(log)
        if stamp is not None:
            clarify_target(
                server,
                int(clarification[1]),
                str(log.get("player_id_1") or ""),
                clarification[2],
                admin.read_context(api),
                stamp,
            )
        return True
    match = re.fullmatch(r"!voice\s+([1-9][0-9]{0,17})\s+(ok|still)", text, re.I)
    if match:
        from rcon.leadership_vote.domain import event_time

        stamp = event_time(log)
        if stamp is None:
            return True
        _answer(
            server,
            int(match[1]),
            str(log.get("player_id_1") or ""),
            match[2].lower() == "ok",
            admin.read_context(api),
            stamp,
            by_event=True,
        )
    return True


def private_question_unavailable(sess, delivery):
    """A single game hint only when Discord confirms the direct private reply was unavailable."""
    admin.votes.lock(sess, delivery.payload["server_number"])
    event = sess.scalar(
        select(AdminIncidentEvent).where(
            AdminIncidentEvent.incident_id == delivery.incident_id,
            AdminIncidentEvent.event_type == "report_admin",
        )
    )
    if not event:
        return
    v = event.payload.get("voice", {})
    if (
        v.get("phase") != "awaiting_answer"
        or v.get("witness_route") != "discord"
        or time.time() >= v["deadline"]
        or v.get("discord_hint_queued")
    ):
        return
    _message(
        sess,
        event,
        "discord_reply",
        v["witness_id"],
        v["witness_session"],
        locale=delivery.payload["locale"],
    )
    _replace(event, discord_hint_queued=True)


def flush_messages(api, server):
    """Claim each informational PC receipt before sending; no action records or retries."""
    if not enabled(server):
        return
    from rcon.voice_language import render

    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        job = sess.scalar(
            select(AdminIncidentEvent)
            .join(AdminIncident)
            .where(
                AdminIncident.server_number == server,
                AdminIncidentEvent.event_type == "voice_game_message",
                AdminIncidentEvent.payload["status"].as_string() == "pending",
            )
            .order_by(AdminIncidentEvent.id)
            .limit(1)
        )
        if not job:
            return
        p = job.payload
        now = time.time()
        if (
            now >= p["expires"]
            or admin.session_token(sess, server, p["recipient"], now) != p["session"]
        ):
            job.payload = {**p, "status": "expired"}
            return
        case = sess.get(AdminIncidentEvent, p["event_id"])
        if p["key"] == "discord_reply":
            v = case.payload.get("voice", {})
            if v.get("phase") != "awaiting_answer" or now >= v["deadline"]:
                job.payload = {**p, "status": "expired"}
                return
        msg = render(
            sess,
            p["key"],
            p["locale"],
            target=case.incident.target_name or "",
            case=str(case.id),
        )
        if p["key"] == "clarify":
            msg += "\n" + render(sess, "pc_clarify", p["locale"], case=str(case.id))
        job_id, recipient = job.id, p["recipient"]
        job.payload = {**p, "status": "sending"}

    sent = _send(api, recipient, msg)
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        job = sess.get(AdminIncidentEvent, job_id)
        if job and job.payload["status"] == "sending":
            job.payload = {**job.payload, "status": "sent" if sent else "unknown"}
