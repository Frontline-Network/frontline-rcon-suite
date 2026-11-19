"""Collect the reason for a bare !admin in the reporter's existing chat incident."""

import time
from datetime import datetime, timezone

from sqlalchemy import select

from rcon import admin_incidents as incidents
from rcon import report_admin
from rcon.incident_notifications import notify_incident_reporter
from rcon.leadership_vote.domain import event_time
from rcon.leadership_vote.storage import lock
from rcon.models import AdminIncident

WINDOW = 120
PROMPT = (
    "Hi! How can I help? Please tell me what happened. "
    "If someone is involved, include their player or squad name. "
    "Reply in your own language in game chat within two minutes. "
    "Your team or squad can see your chat reply."
)
EXPLICIT_PROMPT = (
    "Hi! How can I help? Please type !admin followed by what happened in game chat. "
    "You can write in your own language."
)

_MORE_DETAIL = {
    "en": (
        {"hi", "hello", "help", "help me", "please help"},
        "What happened in the game? A short description is enough.",
    ),
    "de": (
        {"hallo", "hilfe", "bitte hilfe"},
        "Was ist im Spiel passiert? Eine kurze Beschreibung reicht.",
    ),
    "fr": (
        {"bonjour", "salut", "aide", "à l’aide"},
        "Que s’est-il passé en jeu ? Une courte description suffit.",
    ),
    "pl": (
        {"hej", "pomocy", "proszę o pomoc"},
        "Co się stało w grze? Wystarczy krótki opis.",
    ),
    "nl": (
        {"hallo daar", "help mij"},
        "Wat is er in het spel gebeurd? Een korte beschrijving is genoeg.",
    ),
}


def ask_for_detail(api, incident_id, log):
    text = str(log["sub_content"]).strip().casefold().strip(" .!?")
    message = next((msg for words, msg in _MORE_DETAIL.values() if text in words), None)
    if message is None:
        return False
    with incidents.enter_session() as sess:
        row = sess.get(AdminIncident, incident_id, with_for_update=True)
        if not row or not matches(sess, row, event_time(log)):
            return False
        prompt = row.reporter_context["reason_prompt"]
        if prompt.get("asked_again"):
            return True
        row.reporter_context = {
            **row.reporter_context,
            "reason_prompt": {**prompt, "asked_again": True},
        }
        recipient = {"reporter_id": row.reporter_id, "reporter_name": row.reporter_name}
    try:
        notify_incident_reporter(api, recipient, message=message)
    except Exception:
        incidents.logger.exception("Unable to deliver the follow-up question")
    return True


def ask(api, incident, log):
    pid, server = incident["reporter_id"], incident["server_number"]
    stamp = event_time(log)
    now = time.time()
    if stamp is None or not 0 <= now - stamp <= 30:
        return
    with incidents.enter_session() as sess:
        token = report_admin.session_token(sess, server, pid, stamp)
    if not notify_incident_reporter(
        api, incident, message=PROMPT if token is not None else EXPLICIT_PROMPT
    ):
        return
    with incidents.enter_session() as sess:
        row = sess.get(AdminIncident, incident["id"], with_for_update=True)
        if row and row.status == "new" and row.revision == 1:
            row.reporter_context = {
                **row.reporter_context,
                "reason_prompt": {"asked": now, "session": token},
            }


def pending(log, server):
    text = str(log.get("sub_content") or "").strip()
    pid, stamp = log.get("player_id_1"), event_time(log)
    if not pid or not text or stamp is None or not 0 <= time.time() - stamp <= 30:
        return None
    if text.startswith(("!", "/")) and not text.lower().startswith("!admin "):
        return None
    with incidents.enter_session() as sess:
        row = sess.scalar(
            select(AdminIncident)
            .where(
                AdminIncident.server_number == server,
                AdminIncident.reporter_id == str(pid),
                AdminIncident.source == "chat",
                AdminIncident.status == "new",
                AdminIncident.revision == 1,
                AdminIncident.created_at
                >= datetime.fromtimestamp(stamp - WINDOW, timezone.utc),
                AdminIncident.reporter_context["reason_prompt"]["asked"]
                .as_float()
                .is_not(None),
            )
            .order_by(AdminIncident.created_at.desc())
            .limit(1)
        )
        if row and matches(
            sess, row, stamp, explicit=text.lower().startswith("!admin ")
        ):
            return row.id
    return None


def matches(sess, row, stamp, *, explicit=False):
    prompt = (row.reporter_context or {}).get("reason_prompt")
    return bool(
        prompt
        and row.status == "new"
        and not row.assigned_to
        and row.revision == 1
        and (prompt["session"] is not None or explicit)
        and prompt["asked"] < stamp <= prompt["asked"] + WINDOW
        and time.time() <= prompt["asked"] + WINDOW
        and report_admin.session_token(sess, row.server_number, row.reporter_id, stamp)
        == prompt["session"]
    )


def complete(incident_id, server, pid, stamp, parsed, reporter, context):
    with incidents.enter_session() as sess:
        lock(sess, server)
        row = sess.get(AdminIncident, incident_id, with_for_update=True)
        if (
            not row
            or row.server_number != server
            or row.reporter_id != pid
            or not matches(sess, row, stamp, explicit=True)
        ):
            return None
        row.reason, row.raw_message = parsed["reason"], parsed["raw_message"]
        row.reporter_context = reporter
        row.subjects.extend(
            incidents._subject_from_payload(s, actor="system:chat")
            for s in parsed["subjects"]
        )
        incidents._sync_primary_target(row)
        row.dedupe_key = incidents._dedupe_key(
            server,
            pid,
            row.raw_message,
            subjects=parsed["subjects"],
            target_id=row.target_id,
        )
        row.revision += 1
        now = incidents._utcnow()
        row.updated_at = now
        row.events.append(incidents._event("system:chat", "report_reason_received"))
        sess.flush()
        if context is not None:
            try:
                with sess.begin_nested():
                    report_admin.enqueue(sess, row, context, now.timestamp())
            except Exception:
                incidents.logger.exception(
                    "Unable to classify the supplied reason; preserved for admin review"
                )
        return row.to_dict(include_events=True), True
