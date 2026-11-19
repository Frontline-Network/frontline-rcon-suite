"""Private Discord player interactions for an explicitly published server panel."""

from __future__ import annotations

import hashlib
import asyncio
import re
from datetime import datetime, timedelta, timezone
from http.client import HTTPSConnection
import json
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from .config import get_settings
from .db import SessionLocal
from .discord_client import DiscordClient
from .models import EventReceipt, Integration
from .player_callback import effective_origin
from . import report_picker as picker
from .player_models import PlayerDMPreference, PlayerPanel, PrivateReply
from .security import decrypt, encrypt

# The published panel is shared; the private form uses Discord's interface locale.
# Player-specific case texts and action labels are rendered by the RCON backend.
UI = {
    "report": (
        "Vorfall melden",
        "Report incident",
        "Signaler un incident",
        "Zgłoś incydent",
        "Incident melden",
    ),
    "dm_on": (
        "Direktnachrichten einschalten",
        "Enable direct messages",
        "Activer les messages privés",
        "Włącz wiadomości prywatne",
        "Privéberichten inschakelen",
    ),
    "dm_off": (
        "Direktnachrichten ausschalten",
        "Disable direct messages",
        "Désactiver les messages privés",
        "Wyłącz wiadomości prywatne",
        "Privéberichten uitschakelen",
    ),
    "list": (
        "Meine Meldungen",
        "My reports",
        "Mes signalements",
        "Moje zgłoszenia",
        "Mijn meldingen",
    ),
    "language": ("Meine Sprache", "My language", "Ma langue", "Mój język", "Mijn taal"),
    "target": (
        "Spielername oder Rolle",
        "Player name or role",
        "Nom du joueur ou rôle",
        "Nazwa gracza lub rola",
        "Spelernaam of rol",
    ),
    "message": (
        "Was ist passiert?",
        "What happened?",
        "Que s’est-il passé ?",
        "Co się stało?",
        "Wat is er gebeurd?",
    ),
    "language_value": (
        "Sprachcode, z. B. de, fr, nl",
        "Language code, e.g. en, fr, pl",
        "Code de langue, p. ex. fr, de, nl",
        "Kod języka, np. pl, de, fr",
        "Taalcode, bijv. nl, en, de",
    ),
    "link": (
        "Spielkonto verknüpfen",
        "Link game account",
        "Lier le compte de jeu",
        "Połącz konto gry",
        "Spelaccount koppelen",
    ),
    "player": (
        "Dein Spielername oder deine Spiel-ID",
        "Your game name or ID",
        "Votre nom en jeu ou identifiant",
        "Twoja nazwa lub ID w grze",
        "Je spelernaam of spel-ID",
    ),
    "verify": (
        "Code bestätigen",
        "Confirm code",
        "Confirmer le code",
        "Potwierdź kod",
        "Code bevestigen",
    ),
    "code": (
        "Privater Code aus dem Spiel",
        "Private code received in game",
        "Code privé reçu en jeu",
        "Prywatny kod z gry",
        "Privécode uit het spel",
    ),
    "clarify": (
        "Spieler angeben",
        "Identify player",
        "Préciser le joueur",
        "Wskaż gracza",
        "Speler opgeven",
    ),
    "help": (
        "Bitte öffne „Meine Meldungen“, um den aktuellen Stand zu prüfen.",
        "Open My reports to check the latest status.",
        "Ouvrez Mes signalements pour consulter le statut.",
        "Otwórz Moje zgłoszenia, aby sprawdzić stan.",
        "Open Mijn meldingen om de status te bekijken.",
    ),
    "invalid": (
        "Dieser Zugang ist nicht mehr verfügbar.",
        "This player panel is unavailable.",
        "Ce panneau est indisponible.",
        "Ten panel jest niedostępny.",
        "Dit paneel is niet beschikbaar.",
    ),
}
LANGUAGES = ("de", "en", "fr", "pl", "nl")
FORM_FIELDS = {
    "report": (("target", 255, False), ("message", 2000, True)),
    "clarify": (("target", 255, True),),
    "language": (("language_value", 35, True),),
    "link": (("player", 255, True),),
    "verify": (("code", 32, True),),
}
ACTIONS = {
    *FORM_FIELDS,
    "list",
    "home",
    "dm_on",
    "dm_off",
    "resolved",
    "persisting",
    "squad",
    "pick_player",
    "pick_report",
    "pick_clarify",
    "legacy_form",
}
COMPONENT = re.compile(r"vp:([0-9a-f]{32}):([a-z_]{2,16})(?::([0-9a-fA-F-]{36}))?")
SNOWFLAKE = re.compile(r"[0-9]{1,32}")
INCIDENT_ID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


def ui(locale, key):
    lang = str(locale or "").lower().split("-")[0]
    labels = UI[key] if key in UI else picker.TEXT[key]
    return (
        labels[LANGUAGES.index(lang)]
        if lang in LANGUAGES
        else f"{labels[0]} / {labels[1]}"
    )


def button(panel, operation, label, incident_id=""):
    identifier = f"vp:{panel.id}:{operation}"
    if incident_id:
        identifier += f":{incident_id}"
    return {"type": 2, "style": 2, "label": label[:80], "custom_id": identifier}


def public_message(panel):
    buttons = [
        button(panel, key, ui("", key)) for key in ("report", "list", "language")
    ]
    return {
        "content": f"RCON{panel.server_number} · Spieler-Service / Player support",
        "components": [{"type": 1, "components": buttons}],
        "allowed_mentions": {"parse": []},
    }


def private_data(content, components=None):
    return {
        "content": content[:2000],
        "components": components or [],
        "allowed_mentions": {"parse": []},
    }


def case_message(panel, result):
    buttons = []
    for action in result.get("actions", []):
        op = action.get("operation")
        if op == "dm":
            op = "dm_on" if action.get("enabled") is True else "dm_off"
        if op == "answer":
            op = action.get("answer")
        if op not in ACTIONS or not isinstance(action.get("label"), str):
            continue
        incident = str(action.get("incident_id") or "")
        if incident and not INCIDENT_ID.fullmatch(incident):
            continue
        if op in {"resolved", "persisting", "clarify"} and not incident:
            continue
        buttons.append(button(panel, op, action["label"], incident))
    rows = [
        {"type": 1, "components": buttons[i : i + 5]}
        for i in range(0, min(25, len(buttons)), 5)
    ]
    return private_data(str(result["content"]), rows)


def modal(panel, op, case_id, locale, title=None):
    components = []
    for name, length, required in FORM_FIELDS[op]:
        components.append(
            {
                "type": 1,
                "components": [
                    {
                        "type": 4,
                        "custom_id": name,
                        "style": 2 if name == "message" else 1,
                        "label": (
                            title if op == "clarify" and title else ui(locale, name)
                        )[:45],
                        "max_length": length,
                        "required": required,
                    }
                ],
            }
        )
    return {
        "type": 9,
        "data": {
            "custom_id": button(panel, op, "", case_id)["custom_id"],
            "title": (title or ui(locale, op))[:45],
            "components": components,
        },
    }


def operation_args(payload, op, case_id):
    if op in {"pick_report", "pick_clarify"}:
        if payload["type"] != 5 or bool(case_id) != (op == "pick_clarify"):
            raise ValueError("Invalid roster form")
        fields = {
            row["component"]["custom_id"]: row["component"]
            for row in payload["data"]["components"]
            if row.get("type") == 18
        }
        target = fields["target_ref"]
        values = target.get("values")
        if (
            target["type"] != 3
            or not isinstance(values, list)
            or len(values) != 1
            or not picker.REF.fullmatch(values[0])
        ):
            raise ValueError("Invalid roster choice")
        args = {"target_ref": values[0]}
        op = "clarify" if case_id else "report"
        if not case_id:
            message = fields["message"]["value"].strip()
            if not 0 < len(message) <= 2000:
                raise ValueError("Invalid report text")
            args["message"] = message
    elif op in FORM_FIELDS:
        if payload["type"] != 5:
            raise ValueError("Expected a form submission")
        fields = {
            v["custom_id"]: str(v.get("value") or "").strip()
            for row in payload["data"].get("components", [])
            for v in row.get("components", [])
        }
        for key, length, required in FORM_FIELDS[op]:
            if (required and not fields.get(key)) or len(fields.get(key, "")) > length:
                raise ValueError("Invalid form field")
        args = {k: fields.get(k, "") for k, _, _ in FORM_FIELDS[op]}
        if op == "language":
            args = {"language": args["language_value"]}
    elif payload["type"] != 3:
        raise ValueError("Expected a button interaction")
    elif op in {"resolved", "persisting"}:
        args, op = {"answer": op}, "answer"
    elif op in {"dm_on", "dm_off"}:
        args, op = {"enabled": op == "dm_on"}, "dm"
    else:
        args = {}
    if case_id:
        args["incident_id"] = case_id
    return op, args


class PrivateReplyError(ValueError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Discord interaction status {status}")


def private_reply(token, data):
    """Edit an ephemeral reply; avoid emitting the webhook token to HTTP request logs."""
    settings = get_settings()
    if settings.dry_run:
        return
    if not SNOWFLAKE.fullmatch(settings.discord_application_id) or not token:
        raise ValueError("Missing Discord interaction credentials")
    path = f"/api/v10/webhooks/{settings.discord_application_id}/{quote(token, safe='')}/messages/@original"
    client = HTTPSConnection("discord.com", timeout=8)
    try:
        client.request(
            "PATCH",
            path,
            body=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        response = client.getresponse()
        response.read()
        if not 200 <= response.status < 300:
            raise PrivateReplyError(response.status)
    finally:
        client.close()


def active_integration(session, panel):
    integration = session.get(Integration, panel.installation_id) if panel else None
    return (
        integration
        if integration
        and integration.enabled
        and integration.guild_id == panel.guild_id
        else None
    )


def _panel_post(session, panel, integration, actor, interaction_id, op, args, post):
    response = post(
        f"{effective_origin(session, panel, integration)}/api/discord/v1/player-reports",
        headers={
            "Authorization": f"Bearer {decrypt(integration.action_capability_ciphertext)}"
        },
        json={
            "interaction_id": interaction_id,
            "discord_user_id": actor,
            "guild_id": panel.guild_id,
            "channel_id": panel.channel_id,
            "installation_id": panel.installation_id,
            "server_number": panel.server_number,
            "operation": op,
            "arguments": args,
        },
        timeout=10 if op == "roster" else 30,
        follow_redirects=False,
    )
    response.raise_for_status()
    return response.json()["result"]


def _fetch_picker(panel_id, actor, interaction_id, selected, locale, post):
    with SessionLocal() as session:
        panel = session.get(PlayerPanel, panel_id)
        integration = active_integration(session, panel)
        if not integration:
            return "unavailable", []
        try:
            data = _panel_post(
                session, panel, integration, actor, interaction_id, "roster", {}, post
            )
        except httpx.HTTPStatusError as exc:
            # Older paired RCONs reject unknown operations; their existing form still works.
            if exc.response.status_code == 400:
                return "legacy", []
            raise
        if not isinstance(data.get("players"), list):
            return "unavailable", []
        return picker.picker_view(
            data["players"], selected, lambda key: ui(locale, key)
        )


def _picker_modal(panel, case, locale, options):
    op = "pick_clarify" if case else "pick_report"
    return picker.player_modal(
        button(panel, op, "", case)["custom_id"],
        ui(locale, "clarify" if case else "report"),
        ui(locale, "select_player"),
        ui(locale, "message"),
        options,
        clarify=bool(case),
    )


def _picker_response(panel, case, locale, view, *, deferred=False):
    kind, options = view
    if kind == "player" and not deferred:
        return _picker_modal(panel, case, locale, options)
    if kind == "legacy" and not deferred:
        return modal(panel, "clarify" if case else "report", case, locale)
    if kind in {"empty", "gone", "unavailable", "legacy"}:
        retry_op = (
            "legacy_form" if kind == "legacy" else "clarify" if case else "report"
        )
        text = ui(locale, "report" if kind == "legacy" else kind)
        component = button(
            panel, retry_op, ui(locale, "report" if kind == "legacy" else "retry"), case
        )
    else:
        text = ui(locale, "group" if kind == "group" else "select_player")
        op = "squad" if kind == "group" else "pick_player"
        component = {
            "type": 3,
            "custom_id": button(panel, op, "", case)["custom_id"],
            "options": options,
            "placeholder": text[:150],
            "min_values": 1,
            "max_values": 1,
        }
    data = private_data(text, [{"type": 1, "components": [component]}])
    return {"type": 4, "data": {**data, "flags": 64}}


async def _open_picker(panel, case, locale, actor, payload, selected, tasks, post):
    async def load():
        try:
            return await asyncio.to_thread(
                _fetch_picker, panel.id, actor, payload["id"], selected, locale, post
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return "unavailable", []

    # A modal must be the initial Discord response. A slow RCON still gets
    # a private acknowledgement and a selectable result without repeating the read.
    result = asyncio.create_task(load())
    done, _ = await asyncio.wait({result}, timeout=1.0)
    if done:
        return _picker_response(panel, case, locale, result.result())

    async def finish():
        reply = _picker_response(panel, case, locale, await result, deferred=True)[
            "data"
        ]
        reply.pop("flags", None)
        await asyncio.to_thread(private_reply, payload["token"], reply)

    tasks.add_task(finish)
    return {"type": 5, "data": {"flags": 64}}


def handle_interaction(session, payload, background_tasks, post):
    data = payload.get("data") or {}
    custom_id = str(data.get("custom_id", ""))
    if not custom_id.startswith("vp:"):
        return None
    locale = payload.get("locale")
    reject = {"type": 4, "data": {**private_data(ui(locale, "invalid")), "flags": 64}}
    match = COMPONENT.fullmatch(custom_id)
    actor = str((payload.get("member", {}).get("user") or {}).get("id", ""))
    if (
        not match
        or not SNOWFLAKE.fullmatch(actor)
        or not SNOWFLAKE.fullmatch(str(payload.get("id", "")))
    ):
        return reject
    panel_id, op, case_id = match.groups()
    panel = session.get(PlayerPanel, panel_id)
    if (
        op not in ACTIONS
        or not active_integration(session, panel)
        or not panel.message_id
        or payload.get("guild_id") != panel.guild_id
        or payload.get("channel_id") != panel.channel_id
        or (case_id and not INCIDENT_ID.fullmatch(case_id))
        or (op in {"clarify", "resolved", "persisting"} and not case_id)
    ):
        return reject
    if payload.get("type") == 3 and op in {
        "report",
        "clarify",
        "squad",
        "pick_player",
        "legacy_form",
    }:
        if not payload.get("token"):
            return reject
        if op == "legacy_form":
            return modal(panel, "clarify" if case_id else "report", case_id, locale)
        values = data.get("values")
        if op in {"squad", "pick_player"}:
            if (
                not isinstance(values, list)
                or len(values) != 1
                or not isinstance(values[0], str)
            ):
                return reject
            if op == "pick_player":
                option = next(
                    (
                        opt
                        for row in (payload.get("message") or {}).get("components", [])
                        for menu in row.get("components", [])
                        if menu.get("custom_id") == custom_id
                        for opt in menu.get("options", [])
                        if opt.get("value") == values[0]
                    ),
                    None,
                )
                if not option or not picker.REF.fullmatch(values[0]):
                    return reject
                return _picker_modal(
                    panel, case_id, locale, [{**option, "default": True}]
                )
            if not picker.GROUP.fullmatch(values[0]):
                return reject
        return _open_picker(
            panel,
            case_id,
            locale,
            actor,
            payload,
            values[0] if op == "squad" else None,
            background_tasks,
            post,
        )
    if payload.get("type") == 3 and op in FORM_FIELDS:
        # Private case buttons already contain the reporter’s translated label.
        # Preserve it when opening a clarification, even if the account UI is
        # configured for a different language.
        message = payload.get("message") or {}
        title = (
            next(
                (
                    c.get("label")
                    for row in message.get("components", [])
                    for c in row.get("components", [])
                    if c.get("custom_id") == custom_id
                ),
                None,
            )
            if message.get("flags", 0) & 64
            else None
        )
        return modal(panel, op, case_id, locale, title)
    try:
        op, args = operation_args(payload, op, case_id)
    except (KeyError, TypeError, ValueError):
        return reject
    token = payload.get("token")
    if not token:
        return reject
    background_tasks.add_task(
        finish_interaction,
        panel_id,
        actor,
        payload["id"],
        token,
        locale,
        op,
        args,
        post,
    )
    return {"type": 5, "data": {"flags": 64}}


def save_latest_interaction(session, model, identities, interaction_id, **fields):
    # Snowflakes are unsigned integers stored as strings. Compare by length
    # then lexically to avoid rounding in SQLite or overflowing a signed bigint.
    current = model.interaction_id
    newer = or_(
        func.length(current) < len(interaction_id),
        (func.length(current) == len(interaction_id)) & (current < interaction_id),
    )
    insert = (
        sqlite_insert
        if session.get_bind().dialect.name == "sqlite"
        else postgres_insert
    )
    changes = {**fields, "interaction_id": interaction_id}
    stmt = insert(model).values(**identities, **changes)
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=list(identities), set_=changes, where=newer
        )
    )


def finish_interaction(panel_id, actor, interaction_id, token, locale, op, args, post):
    try:
        with SessionLocal() as session:
            panel = session.get(PlayerPanel, panel_id)
            integration = active_integration(session, panel)
            if not integration:
                raise ValueError("Inactive panel")
            result = _panel_post(
                session, panel, integration, actor, interaction_id, op, args, post
            )
            preference = session.get(PlayerDMPreference, (panel.installation_id, actor))
            if op in {"list", "home"}:
                actions = list(result.get("actions", []))
                provided = {item.get("operation") for item in actions}
                option = "dm_off" if preference and preference.enabled else "dm_on"
                for key in ("link", "language", option):
                    if key not in provided and not (key == option and "dm" in provided):
                        label = (result.get("labels") or {}).get(key) or ui(
                            result.get("language") or locale, key
                        )
                        actions.append({"operation": key, "label": label})
                result = {**result, "actions": actions}
            reply = case_message(panel, result)
            if op == "dm" and result.get("ok", True):
                save_latest_interaction(
                    session,
                    PlayerDMPreference,
                    {
                        "installation_id": panel.installation_id,
                        "discord_user_id": actor,
                    },
                    interaction_id,
                    enabled=args["enabled"],
                )
            session.commit()
            incident = str(result.get("incident_id") or "")
            # Publish the initial response before making its token available
            # to the status worker, so it can never overwrite a later update.
            if INCIDENT_ID.fullmatch(incident):
                private_reply(token, reply)
                now = datetime.now(timezone.utc)
                session.execute(
                    delete(PrivateReply)
                    .where(PrivateReply.expires_at <= now)
                    .execution_options(synchronize_session="fetch")
                )
                save_latest_interaction(
                    session,
                    PrivateReply,
                    {
                        "panel_id": panel.id,
                        "discord_user_id": actor,
                        "incident_id": incident,
                    },
                    interaction_id,
                    encrypted_token=encrypt(token),
                    expires_at=now + timedelta(minutes=14),
                )
                session.commit()
                return
    except (
        httpx.HTTPError,
        HTTPException,
        ValueError,
        KeyError,
        IntegrityError,
        OSError,
    ):
        reply = private_data(ui(locale, "help"))
    try:
        private_reply(token, reply)
    except (OSError, ValueError):
        # The durable case remains visible through My reports.
        return


class NotificationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = Field(max_length=16)
    label: str = Field(min_length=1, max_length=80)
    incident_id: str | None = Field(default=None, max_length=36)
    answer: str | None = Field(default=None, max_length=16)
    enabled: bool | None = None


class PlayerNotification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    installation_id: str = Field(min_length=1, max_length=64)
    server_number: int = Field(ge=1, le=10000)
    discord_user_id: str = Field(pattern=r"^[0-9]{1,32}$")
    incident_id: str = Field(
        pattern=r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"
    )
    content: str = Field(min_length=1, max_length=2000)
    actions: list[NotificationAction] = Field(default_factory=list, max_length=25)
    send_dm: bool = False


def private_dm(user_id, body, nonce):
    client = DiscordClient()
    if client.settings.dry_run:
        return
    if not client.settings.discord_bot_token:
        raise ValueError("Discord not configured")
    headers = {"Authorization": f"Bot {client.settings.discord_bot_token}"}
    with client.client as http:
        dm = http.post(
            "https://discord.com/api/v10/users/@me/channels",
            headers=headers,
            json={"recipient_id": user_id},
        )
        dm.raise_for_status()
        channel_id = str(dm.json()["id"])
        result = http.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json={**body, "nonce": nonce, "enforce_nonce": True},
        )
        result.raise_for_status()


def patch_notification(session, panel, notification, sequence):
    """Serialize edits to a single private reply and persist its newest version.

    The conditional write takes a transaction lock on SQLite and PostgreSQL.
    A lost HTTP response is safe to retry: PATCH replaces the same message.
    A stale request can never replace a newer observed state.
    """
    stamp = datetime.now(timezone.utc)
    where = (
        PrivateReply.panel_id == panel.id,
        PrivateReply.discord_user_id == notification.discord_user_id,
        PrivateReply.incident_id == notification.incident_id,
    )
    affected = session.execute(
        update(PrivateReply)
        .where(
            *where,
            PrivateReply.expires_at > stamp,
            PrivateReply.notification_sequence <= sequence,
            PrivateReply.applied_sequence < sequence,
        )
        .values(notification_sequence=sequence)
        .execution_options(synchronize_session=False)
    )
    if affected.rowcount != 1:
        active = session.scalar(
            select(PrivateReply.notification_sequence).where(
                *where, PrivateReply.expires_at > stamp
            )
        )
        session.commit()
        return (
            "disabled"
            if active is None
            else ("stale" if active > sequence else "already_claimed")
        )
    row = session.scalar(
        select(PrivateReply).where(*where).execution_options(populate_existing=True)
    )
    try:
        private_reply(
            decrypt(row.encrypted_token), case_message(panel, notification.model_dump())
        )
    except PrivateReplyError as exc:
        if exc.status in {401, 403, 404, 410}:
            session.delete(row)
            result = "disabled"
        else:
            result = (
                "retry" if exc.status == 429 or exc.status >= 500 else "unavailable"
            )
    except OSError:
        result = "retry"
    except ValueError:
        result = "unavailable"
    else:
        row.applied_sequence = sequence
        result = "sent"
    session.commit()
    return result


def notify_player(session, integration, notification, key):
    match = re.fullmatch(
        r"voice:" + re.escape(integration.installation_id) + r":([1-9][0-9]{0,18})",
        key or "",
    )
    if not match or int(match[1]) > (1 << 63) - 1:
        raise HTTPException(status_code=400, detail="Invalid voice delivery key")
    panel = session.scalar(
        select(PlayerPanel).where(
            PlayerPanel.installation_id == integration.installation_id,
            PlayerPanel.server_number == notification.server_number,
            PlayerPanel.guild_id == integration.guild_id,
            PlayerPanel.message_id.is_not(None),
        )
    )
    if not panel:
        raise HTTPException(status_code=404, detail="Unknown player panel")
    actor = notification.discord_user_id
    session.execute(
        delete(PrivateReply)
        .where(PrivateReply.expires_at <= datetime.now(timezone.utc))
        .execution_options(synchronize_session="fetch")
    )
    patch = patch_notification(session, panel, notification, int(match[1]))
    preference = session.get(PlayerDMPreference, (panel.installation_id, actor))
    status = {
        "accepted": True,
        "ephemeral_updated": patch == "sent",
        "dm_sent": False,
        "retry_ephemeral": patch == "retry",
    }
    if patch == "stale":
        return {**status, "delivery": "already_claimed"}
    if not (notification.send_dm and preference and preference.enabled):
        return {**status, "delivery": "unavailable" if patch == "retry" else patch}
    fingerprint = hashlib.sha256(
        json.dumps(
            [
                integration.installation_id,
                panel.id,
                actor,
                notification.incident_id,
                key,
            ]
        ).encode()
    ).hexdigest()
    insert = (
        sqlite_insert
        if session.get_bind().dialect.name == "sqlite"
        else postgres_insert
    )
    claim = session.execute(
        insert(EventReceipt)
        .values(
            idempotency_key=f"voice-player-dm:{fingerprint}",
            installation_id=integration.installation_id,
            event_id=0,
            event_type="voice_player_dm",
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(EventReceipt.idempotency_key)
    ).scalar_one_or_none()
    session.commit()
    if claim is None:
        return {
            **status,
            "delivery": "sent" if status["ephemeral_updated"] else "already_claimed",
        }
    # DMs create a new message. Claim once before sending; reopening the private
    # guild panel always remains available if Discord or the client disconnects.
    url = f"https://discord.com/channels/{panel.guild_id}/{panel.channel_id}/{panel.message_id}"
    dm = private_data(
        notification.content,
        [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "url": url,
                        "label": "RCON" + str(panel.server_number),
                    }
                ],
            }
        ],
    )
    try:
        private_dm(actor, dm, fingerprint[:24])
        status["dm_sent"] = True
    except (httpx.HTTPError, ValueError):
        pass
    return {
        **status,
        "delivery": (
            "sent"
            if status["ephemeral_updated"] or status["dm_sent"]
            else "unavailable"
        ),
    }
