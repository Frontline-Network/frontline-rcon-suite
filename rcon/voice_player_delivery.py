"""Persist private Discord updates in the same transaction as their voice case."""

from datetime import datetime, timezone

from sqlalchemy import select

from rcon import voice_language as lang
from rcon.voice_player_store import VoicePlayerDelivery


def reporter_discord_id(sess, incident):
    discord_id = (incident.reporter_context or {}).get("voice_discord_id")
    if discord_id and any(
        e.actor == "discord:voice-player" and e.event_type == "created"
        for e in incident.events
    ):
        return str(discord_id)
    return (
        lang.linked_discord_id(sess, incident.reporter_id)
        if incident.reporter_id
        else None
    )


def answer_actions(sess, incident_id, locale):
    return [
        {
            "operation": "answer",
            "incident_id": incident_id,
            "answer": value,
            "label": lang.render(sess, key, locale),
        }
        for value, key in (("resolved", "fixed"), ("persisting", "still_silent"))
    ]


def status_key(event):
    if not event:
        return "received"
    p = event.payload
    v = p.get("voice") or {}
    phase = v.get("phase")
    if phase == "resolved":
        return "resolved"
    if phase not in {
        "notice_pending",
        "notice_sending",
        "notice_sent",
        "question_sending",
        "awaiting_answer",
        "kick_ready",
        None,
    }:
        return v.get("message_key") or {
            "kicked": "kicked",
            "unknown": "unconfirmed",
            "duplicate": "duplicate",
        }.get(phase, "manual")
    if v.get("notice_sent_at"):
        return "notice_external" if v.get("external") else "notice_sent"
    return "manual" if p.get("status") == "manual" else "received"


def _outbox(
    sess, incident, discord_id, kind, key, locale, target, *, question=False, dm=False
):
    if not discord_id:
        return
    found = sess.scalar(
        select(VoicePlayerDelivery.id).where(
            VoicePlayerDelivery.incident_id == incident.id,
            VoicePlayerDelivery.kind == kind,
            VoicePlayerDelivery.discord_id == str(discord_id),
        )
    )
    if found is not None:
        return
    sess.add(
        VoicePlayerDelivery(
            incident_id=incident.id,
            discord_id=str(discord_id),
            kind=kind,
            done=False,
            attempts=0,
            due=datetime.now(timezone.utc),
            payload={
                "key": key,
                "locale": locale,
                "target": target,
                "question": question,
                "send_dm": dm,
                "server_number": incident.server_number,
            },
        )
    )


def queue_update(sess, event, kind):
    p, incident = event.payload, event.incident
    voice = p.get("voice") or {}
    reporter = reporter_discord_id(sess, incident)
    locale = (
        voice.get("reporter_language")
        or (incident.reporter_context or {}).get("voice_locale")
        or "de+en"
    )
    target = p.get("target_name") or incident.target_name or ""
    if kind == "question":
        witness = voice.get("witness_id")
        discord_id = lang.linked_discord_id(sess, witness) if witness else None
        if discord_id:
            language = (
                locale
                if discord_id == reporter
                else lang.preferred_language(sess, discord_id=discord_id)
            )
            _outbox(
                sess,
                incident,
                discord_id,
                kind,
                "question",
                language,
                target,
                question=True,
            )
    elif kind in {"notice", "final"} and reporter:
        key = (
            status_key(event)
            if kind == "final"
            else ("notice_external" if voice.get("external") else "notice_sent")
        )
        _outbox(sess, incident, reporter, kind, key, locale, target, dm=kind == "final")


def queue_admin_change(sess, incident, status):
    event = next(
        (
            e
            for e in incident.events
            if e.event_type == "report_admin" and e.payload.get("voice")
        ),
        None,
    )
    if not event:
        return
    discord_id = reporter_discord_id(sess, incident)
    locale = event.payload["voice"].get("reporter_language") or "de+en"
    _outbox(
        sess,
        incident,
        discord_id,
        status,
        status,
        locale,
        incident.target_name or "",
        dm=True,
    )
