"""Player-only callback. Discord authenticates the interaction before relaying it."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from sqlalchemy import and_, delete, or_, select

from api.auth import api_response
from api.decorators import require_http_methods
from api.discord_integration import _authorized_integration
from api.mobile import _error, _json_body
from api.multi_servers import forward_mobile_request_to_server
from rcon import voice_language as language
from rcon.admin_incidents import _is_commander, create_incident
from rcon.api_commands import get_rcon_api
from rcon.leadership_vote.service import read_context
from rcon.leadership_vote.storage import lock
from rcon.models import AdminIncident, AdminIncidentEvent, enter_session
from rcon.utils import get_server_number
from rcon.voice_player_delivery import answer_actions, status_key
from rcon.voice_player_store import VoiceDraft, VoiceLinkChallenge

COMMAND = "discord_player_reports"


def _exact(players, name):
    name = name.strip().casefold()
    matches = [
        p
        for p in players
        if name
        and name
        in {
            str(p.get("player_id") or "").casefold(),
            str(p.get("name") or p.get("player_name") or "").casefold(),
        }
        and p.get("online") is not False
    ]
    return matches[0] if len(matches) == 1 else None


def _roster_ref(server, actor, player):
    # Keep platform account IDs out of Discord components. In Vietnam player_id is the EOS ID.
    data = f"voice-roster:{server}:{actor}:{player['player_id']}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), data, hashlib.sha256).hexdigest()[:32]


def _roster(server, actor):
    players = read_context(get_rcon_api())["players"]
    return {
        "players": [
            {
                "ref": _roster_ref(server, actor, p),
                "name": str(p.get("name") or p.get("player_name") or "–"),
                "team": str(p.get("faction") or p.get("team") or "").upper(),
                "squad": str(p.get("unit_name") or ""),
                "commander": _is_commander(p),
                "role": str(p.get("role") or ""),
            }
            for p in players
            if p.get("online") is not False and p.get("player_id")
        ]
    }


def _content(sess, key, locale, **values):
    return {"content": language.render(sess, key, locale, **values)}


def _arg(arguments, name, maximum, optional=False):
    value = arguments.get(name, "") if optional else arguments.get(name)
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (not optional and not value.strip())
    ):
        raise ValueError("Invalid " + name)
    return value.strip()


def _digest(server, discord_id, game_id, code):
    body = f"voice-link:{server}:{discord_id}:{game_id}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), body, hashlib.sha256).hexdigest()


def _link(server, actor, args):
    api = get_rcon_api()
    target = _exact(read_context(api)["players"], _arg(args, "player", 255))
    now = datetime.fromtimestamp(time.time(), timezone.utc)
    with enter_session() as sess:
        lock(sess, server)
        locale = language.preferred_language(sess, discord_id=actor)
        failed = _content(sess, "link_failed", locale)
        if not target:
            return failed
        pid = str(target["player_id"])
        if language.linked_discord_id(sess, pid) not in {None, actor}:
            return failed
        sess.execute(
            delete(VoiceLinkChallenge).where(
                VoiceLinkChallenge.created < now - timedelta(minutes=5)
            )
        )
        prior = sess.scalar(
            select(VoiceLinkChallenge)
            .where(
                VoiceLinkChallenge.server == server,
                or_(
                    VoiceLinkChallenge.discord_id == actor,
                    VoiceLinkChallenge.game_id == pid,
                ),
                VoiceLinkChallenge.created > now - timedelta(minutes=1),
            )
            .limit(1)
        )
        if prior:
            return failed
        code = f"{secrets.randbelow(100000000):08d}"
        digest = _digest(server, actor, pid, code)
        sess.merge(
            VoiceLinkChallenge(
                server=server,
                discord_id=actor,
                game_id=pid,
                created=now,
                digest=digest,
                attempts=0,
                delivered=False,
            )
        )
        prompt = language.render(
            sess, "link_code", language.preferred_language(sess, game_id=pid), case=code
        )
    try:
        with api.without_retries():
            sent = api.message_player(pid, prompt, save_message=False) is True
    except Exception:
        sent = False
    with enter_session() as sess:
        lock(sess, server)
        row = sess.get(VoiceLinkChallenge, (server, actor))
        if not sent or not row or row.digest != digest:
            return failed
        row.delivered = True
        return {
            **_content(sess, "link_begin", locale),
            "actions": [
                {
                    "operation": "verify",
                    "label": language.render(sess, "verify_code", locale),
                }
            ],
        }


def _verify(sess, server, actor, args, locale):
    lock(sess, server)
    code = _arg(args, "code", 32)
    row = sess.get(VoiceLinkChallenge, (server, actor))
    failed = _content(sess, "link_failed", locale)
    if not row or not row.delivered or row.attempts >= 5:
        return failed
    created = (
        row.created if row.created.tzinfo else row.created.replace(tzinfo=timezone.utc)
    )
    if not 0 <= time.time() - created.timestamp() < 300:
        sess.delete(row)
        return failed
    row.attempts += 1
    if not hmac.compare_digest(row.digest, _digest(server, actor, row.game_id, code)):
        return failed
    language.link_verified(sess, game_id=row.game_id, discord_id=actor)
    sess.delete(row)
    return _content(sess, "linked", locale)


def _report(server, actor, interaction, args, clarify=False):
    context = read_context(get_rcon_api())
    now = datetime.fromtimestamp(time.time(), timezone.utc)
    draft_id = (
        str(uuid.UUID(_arg(args, "incident_id", 36)))
        if clarify
        else str(
            uuid.uuid5(
                uuid.NAMESPACE_URL, f"frontline-voice:{server}:{actor}:{interaction}"
            )
        )
    )
    with enter_session() as sess:
        lock(sess, server)
        receipt = sess.scalar(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.idempotency_key == "voice:" + draft_id
            )
        )
        if receipt:
            if (
                receipt.incident.server_number != server
                or receipt.actor != "discord:voice-player"
                or (receipt.incident.reporter_context or {}).get("voice_discord_id")
                != actor
            ):
                raise ValueError("Invalid case")
            locale = receipt.incident.reporter_context["voice_locale"]
            return {
                **_content(sess, "received", locale),
                "incident_id": receipt.incident_id,
            }
        sess.execute(delete(VoiceDraft).where(VoiceDraft.expires < now))
        draft = sess.get(VoiceDraft, draft_id)
        if clarify and (
            not draft or draft.server != server or draft.discord_id != actor
        ):
            raise ValueError("Unknown draft")
        message = draft.message if draft else _arg(args, "message", 2000)
        name = _arg(args, "target", 255, optional=True)
        if "target_ref" in args:
            ref = _arg(args, "target_ref", 32)
            if not re.fullmatch(r"[0-9a-f]{32}", ref):
                raise ValueError("Invalid player selection")
            target = next(
                (
                    p
                    for p in context["players"]
                    if p.get("online") is not False
                    and p.get("player_id")
                    and _roster_ref(server, actor, p) == ref
                ),
                None,
            )
        else:
            target = _exact(context["players"], name)
        pid = language.linked_game_id(sess, actor)
        locale = (
            draft.language
            if draft
            else language.report_language(
                sess,
                message,
                discord_id=actor,
                handles=[
                    p.get("name") or p.get("player_name") or ""
                    for p in context["players"]
                ],
            )
        )
        if not target:
            if not draft:
                sess.add(
                    VoiceDraft(
                        id=draft_id,
                        server=server,
                        discord_id=actor,
                        message=message,
                        language=locale,
                        expires=now + timedelta(minutes=10),
                    )
                )
            return {
                **_content(sess, "exact_target", locale),
                "incident_id": draft_id,
                "actions": [
                    {
                        "operation": "clarify",
                        "incident_id": draft_id,
                        "label": language.render(sess, "enter_name", locale),
                    }
                ],
            }
        received = _content(sess, "received", locale)
    reporter = (
        next((p for p in context["players"] if p.get("player_id") == pid), {})
        if pid
        else {}
    )
    target_name = str(target.get("name") or target.get("player_name"))
    incident, _ = create_incident(
        server_number=server,
        source="manual",
        actor="discord:voice-player",
        reporter_id=pid,
        reporter_name=reporter.get("name"),
        reason=message,
        target_id=target["player_id"],
        target_name=target_name,
        reporter_context={
            "voice_discord_id": actor,
            "voice_locale": locale,
            "online": bool(reporter),
        },
        raw_message=f"!admin {target_name}: {message}",
        idempotency_key="voice:" + draft_id,
        leadership_context={
            **context,
            "voice_discord_intake": True,
            "event_time": time.time(),
        },
    )
    with enter_session() as sess:
        sess.execute(
            delete(VoiceDraft).where(
                VoiceDraft.id == draft_id, VoiceDraft.discord_id == actor
            )
        )
    return {**received, "incident_id": incident["id"]}


def _list(sess, server, actor, locale):
    pid = language.linked_game_id(sess, actor)
    authored = and_(
        AdminIncident.source == "manual",
        AdminIncident.reporter_context["voice_discord_id"].as_string() == actor,
        AdminIncident.events.any(
            and_(
                AdminIncidentEvent.event_type == "created",
                AdminIncidentEvent.actor == "discord:voice-player",
            )
        ),
    )
    if pid:
        authored = or_(
            authored,
            and_(
                AdminIncident.source == "chat",
                AdminIncident.reporter_id == pid,
                AdminIncident.events.any(
                    and_(
                        AdminIncidentEvent.event_type == "created",
                        AdminIncidentEvent.actor == "system:chat",
                    )
                ),
            ),
        )
    cases = sess.scalars(
        select(AdminIncident)
        .where(AdminIncident.server_number == server, authored)
        .order_by(AdminIncident.created_at.desc())
        .limit(8)
    ).all()
    lines, actions = [], []
    for case in cases:
        event = next((e for e in case.events if e.event_type == "report_admin"), None)
        key = status_key(event)
        if case.status in {"resolved", "dismissed"} and key not in {
            "kicked",
            "resolved",
        }:
            key = "closed"
        elif case.status == "claimed":
            key = "claimed"
        case_locale = (
            (
                (event.payload.get("voice") or {}).get("reporter_language")
                if event
                else None
            )
            or (case.reporter_context or {}).get("voice_locale")
            or locale
        )
        text = language.render(
            sess, key, case_locale, target=case.target_name or "", case=case.id[:8]
        )
        created = (
            case.created_at
            if case.created_at.tzinfo
            else case.created_at.replace(tzinfo=timezone.utc)
        )
        lines.append(f"<t:{int(created.timestamp())}:t> · {text}")
    if pid:
        pending = sess.scalars(
            select(AdminIncidentEvent)
            .join(AdminIncident)
            .where(
                AdminIncident.server_number == server,
                AdminIncidentEvent.event_type == "report_admin",
                AdminIncidentEvent.payload["voice"]["witness_id"].as_string() == pid,
                AdminIncidentEvent.payload["voice"]["phase"].as_string()
                == "awaiting_answer",
            )
            .order_by(AdminIncidentEvent.id.desc())
            .limit(2)
        )
        questions = [
            event
            for event in pending
            if (event.payload["voice"].get("deadline") or 0) > time.time()
        ]
        for event in questions:
            witness_locale = (
                event.payload["voice"].get("reporter_language") or locale
                if pid == event.incident.reporter_id
                else locale
            )
            lines.insert(
                0,
                language.render(
                    sess,
                    "question",
                    witness_locale,
                    target=event.incident.target_name or "",
                    case=str(event.id),
                ),
            )
            for action in answer_actions(sess, event.incident_id, witness_locale):
                if len(questions) > 1:
                    action["label"] = (
                        f"{action['label']} · {event.incident.target_name or ''}"[:80]
                    )
                actions.append(action)
    labels = {
        key: language.render(sess, name, locale)
        for key, name in (
            ("link", "link"),
            ("dm_on", "dm_on"),
            ("dm_off", "dm_off"),
            ("language", "lang_button"),
        )
    }
    return {
        "content": (
            "\n".join(lines)[:1900]
            if lines
            else language.render(sess, "no_cases", locale)
        ),
        "actions": actions,
        "language": locale,
        "labels": labels,
    }


def _handle(server, actor, interaction, op, args):
    from rcon.voice_reports import answer

    if op == "roster":
        try:
            return _roster(server, actor)
        except ValueError:  # The recorder has no fresh roster during round changes.
            return {"players": None}

    if op in {"report", "clarify"}:
        return _report(server, actor, interaction, args, clarify=op == "clarify")
    if op == "link":
        return _link(server, actor, args)
    with enter_session() as sess:
        locale = language.preferred_language(sess, discord_id=actor)
        if op in {"list", "home"}:
            return _list(sess, server, actor, locale)
        if op == "verify":
            return _verify(sess, server, actor, args, locale)
        if op == "language":
            language.set_language(sess, _arg(args, "language", 40), discord_id=actor)
            return _content(
                sess, "updated", language.preferred_language(sess, discord_id=actor)
            )
        if op == "dm" and type(args.get("enabled")) is bool:
            # The Discord service owns the DM preference and commits it after this reply.
            return _content(sess, "updated", locale)
        if op != "answer":
            raise ValueError("Unknown operation")
        incident_id = str(uuid.UUID(_arg(args, "incident_id", 36)))
        value = _arg(args, "answer", 12)
        if value not in {"resolved", "persisting"}:
            raise ValueError("Unknown answer")
        pid = language.linked_game_id(sess, actor)
    accepted = bool(pid) and answer(
        server, incident_id, pid, value == "resolved", read_context(get_rcon_api())
    )
    with enter_session() as sess:
        return {
            **_content(sess, "answer_saved" if accepted else "answer_closed", locale),
            "incident_id": incident_id,
        }


@csrf_exempt
@require_http_methods(["POST"])
def player_reports(request):
    from rcon.voice_reports import enabled

    integration, denied = _authorized_integration(request, COMMAND)
    if denied:
        return denied
    try:
        data = _json_body(request)
        if str(integration.installation_id) != data.get("installation_id") or (
            not integration.guild_id or integration.guild_id != data.get("guild_id")
        ):
            return _error(COMMAND, "Unknown player panel", 404)
        server = data.get("server_number")
        if type(server) is not int or not 1 <= server <= 10000:
            raise ValueError("Invalid server")
        if server != int(get_server_number()):
            if data.get("forwarded"):
                return _error(COMMAND, "Unavailable profile", 503)
            res = forward_mobile_request_to_server(
                request, server, request.path, data=data
            )
            return HttpResponse(
                res.content, status=res.status_code, content_type="application/json"
            )
        if not enabled(server):
            return _error(COMMAND, "Player reports are disabled", 404)
        actor = data.get("discord_user_id")
        interaction = data.get("interaction_id")
        if not all(
            isinstance(v, str) and re.fullmatch(r"[0-9]{1,22}", v)
            for v in (actor, interaction, data.get("channel_id"))
        ):
            raise ValueError("Invalid interaction")
        args = data.get("arguments", {})
        if not isinstance(args, dict):
            raise ValueError("Invalid arguments")
        result = _handle(server, actor, interaction, data.get("operation"), args)
        return api_response(command=COMMAND, failed=False, result=result)
    except (KeyError, TypeError, ValueError):
        return _error(COMMAND, "Invalid or unavailable player request", 400)
