from __future__ import annotations

import hashlib
import math
from datetime import datetime

import httpx

from .config import Settings, get_settings
from .contracts import IncidentEventEnvelope, ModerationAnalysis
from .report_admin_display import case_fields

SQUAD_LEADER_ROLES = {
    "officer",
    "squadleader",
    "tankcommander",
    "spotter",
    "artilleryobserver",
    "mortarobserver",
    "helicopterlogisticsofficer",
}


def _truncate(value: object, length: int) -> str:
    text = str(value or "-")
    return text if len(text) <= length else f"{text[: length - 1]}…"


def _present(value: object) -> bool:
    return value is not None and value != ""


def _metric(label: str, value: object) -> str | None:
    if not _present(value):
        return None
    return f"**{label}:** {value}"


def _field_block(*values: str | None) -> str:
    return "\n".join(value for value in values if value) or "-"


def _player_stat_fields(snapshot: dict, language: str, *, leader=False) -> list[dict]:
    """Same player statistics for player and squad reports, never squad totals.

    Missing telemetry is not zero. Bulk rosters do not supply round playtime
    (the adapter uses zero), so no KPM can be inferred from that placeholder.
    """
    def number(key):
        value = snapshot.get(key)
        return (
            value
            if type(value) in (int, float) and math.isfinite(value) and value >= 0
            else None
        )

    def metric(label, value):
        return _metric(label, value if value is not None else "–")

    german = language == "de"
    french = language == "fr"
    kills, deaths = number("kills"), number("deaths")
    seconds = number("map_playtime_seconds")
    elapsed = seconds is not None and seconds > 0
    kd = (
        f"{kills / max(deaths, 1):.2f}"
        if kills is not None and deaths is not None
        else None
    )
    kpm = f"{kills / (seconds / 60):.2f}" if kills is not None and elapsed else None
    teamkills = number("teamkills")
    if teamkills is None:
        teamkills = number("team_kills")
    suffix = " · SL" if leader else ""
    return [
        {
            "name": ("⚔️ Kampf" if german else "⚔️ Combat") + suffix,
            "value": _field_block(
                metric("Kills", kills),
                metric("Tode" if german else "Morts" if french else "Deaths", deaths),
                metric("K/D", kd),
                metric("Kampfpunkte" if german else "Score de combat" if french else "Combat score", number("combat")),
            ),
            "inline": True,
        },
        {
            "name": ("⚡ Leistung" if german else "⚡ Performance") + suffix,
            "value": _field_block(
                metric("KPM", kpm),
                metric("Killserie" if german else "Série d’éliminations" if french else "Kill streak", number("kills_streak")),
                metric(
                    "Runden-Spielzeit" if german else "Temps de jeu de la manche" if french else "Round playtime",
                    f"{seconds / 60:.1f} min" if elapsed else None,
                ),
            ),
            "inline": True,
        },
        {
            "name": "⚠️ Teamkills" + suffix,
            "value": _field_block(
                metric("Anzahl" if german else "Nombre" if french else "Count", teamkills),
                metric("Serie" if german else "Série" if french else "Streak", number("teamkills_streak")),
            ),
            "inline": True,
        },
    ]


def _bounded_report_embeds(embeds: list[dict], language: str) -> list[dict]:
    """Discord's text limit is shared by ALL embeds, not per squad/field."""
    def size(embed):
        return (
            len(embed.get("title", ""))
            + len(embed.get("description", ""))
            + len(embed.get("footer", {}).get("text", ""))
            + sum(len(f["name"]) + len(f["value"]) for f in embed.get("fields", []))
        )

    if sum(size(embed) for embed in embeds) <= 5900:
        return embeds
    # Keep the actionable primary case first. The selector and full server-side
    # evidence remain available even if a large multi-squad report is shortened.
    note = (
        "Details gekürzt; vollständigen Report in CRCON öffnen."
        if language == "de"
        else "Détails raccourcis ; ouvrez le signalement complet dans CRCON."
        if language == "fr"
        else "Details shortened; open the full report in CRCON."
    )
    remaining, result = 5900 - len(note) - 3, []
    for original in embeds:
        embed = {
            **original,
            "description": _truncate(original.get("description"), 1200),
            "footer": {"text": _truncate(original.get("footer", {}).get("text"), 512)},
            "fields": [],
        }
        header = size(embed)
        if header > remaining:
            break
        remaining -= header
        for field in original.get("fields", []):
            available = min(1024, remaining - len(field["name"]))
            if available < 2:
                break
            bounded = {**field, "value": _truncate(field["value"], available)}
            embed["fields"].append(bounded)
            remaining -= len(bounded["name"]) + len(bounded["value"])
        result.append(embed)
    result[0]["footer"]["text"] += " | " + note
    return result


def _reporter_context_field(incident: dict, language: str) -> dict:
    """Render the reporter snapshot when a chat report has no safe target.

    A report without a resolved player is still actionable as a workflow item,
    but it must not look as if CRCON failed to collect the live information.
    Keep this deliberately separate from the moderation target: actions may
    only be offered for an explicit target, while the reporter can still be
    contacted through the existing reporter-message action.
    """

    context = incident.get("reporter_context") or {}
    if not isinstance(context, dict):
        context = {}
    reporter_name = context.get("name") or incident.get("reporter_name") or "-"
    reporter_id = context.get("player_id") or incident.get("reporter_id")
    team = context.get("team")
    unit_name = context.get("unit_name")
    role = context.get("role")
    level = context.get("level")
    kills = context.get("kills")
    deaths = context.get("deaths")
    teamkills = context.get("teamkills")
    playtime_seconds = context.get("map_playtime_seconds")
    playtime_hours = (
        float(playtime_seconds) / 3600
        if isinstance(playtime_seconds, (int, float))
        else None
    )
    labels = {
        "de": {
            "name": "Name",
            "id": "ID",
            "team": "Team",
            "unit": "Einheit",
            "role": "Rolle",
            "level": "Level",
            "combat": "Kills/Deaths",
            "teamkills": "Teamkills",
            "playtime": "Spielzeit",
            "title": "👤 Kontext des Melders",
        },
        "en": {
            "name": "Name",
            "id": "ID",
            "team": "Team",
            "unit": "Unit",
            "role": "Role",
            "level": "Level",
            "combat": "Kills/Deaths",
            "teamkills": "Teamkills",
            "playtime": "Playtime",
            "title": "👤 Reporter context",
        },
        "fr": {
            "name": "Nom", "id": "ID", "team": "Équipe", "unit": "Unité",
            "role": "Rôle", "level": "Niveau", "combat": "Éliminations/morts",
            "teamkills": "Teamkills", "playtime": "Temps de jeu", "title": "👤 Contexte du signaleur",
        },
    }.get(language, {})
    details = [_metric(labels["name"], reporter_name)]
    if reporter_id:
        details.append(_metric(labels["id"], f"`{_truncate(reporter_id, 100)}`"))
    details.extend(
        [
            _metric(labels["team"], _display_unit(team) if _present(team) else None),
            _metric(
                labels["unit"],
                _display_unit(unit_name) if _present(unit_name) else None,
            ),
            _metric(labels["role"], role),
            _metric(labels["level"], level),
            _metric(
                labels["combat"],
                f"{kills}/{deaths}" if _present(kills) and _present(deaths) else None,
            ),
            _metric(labels["teamkills"], teamkills),
            _metric(
                labels["playtime"],
                f"{playtime_hours:.1f} h" if playtime_hours is not None else None,
            ),
        ]
    )
    return {"name": labels["title"], "value": _field_block(*details), "inline": False}


def _team_style(team: object, risk_score: float | None) -> tuple[str, int]:
    normalized = str(team or "").casefold()
    if "all" in normalized:
        return "🔵", 0x3B88C3
    if "axis" in normalized:
        return "🔴", 0xD63031
    if risk_score is not None and risk_score >= 0.9:
        return "🚨", 0xD63031
    return "⚪", 0xD85F0E


def _assigned_display_name(value: object) -> str | None:
    assigned = str(value or "").strip()
    if not assigned:
        return None
    if assigned.startswith("discord:"):
        parts = assigned.split(":", 2)
        if len(parts) == 3 and parts[2]:
            return parts[2]
    return assigned


def _manual_processing(incident: dict) -> bool:
    return any(
        event.get("event_type") == "claim"
        and (event.get("payload") or {}).get("mode") == "manual"
        for event in incident.get("events") or []
    )


def _action_actor(event: dict, arguments: dict) -> str:
    discord_actor = arguments.get("discord_actor") or {}
    if isinstance(discord_actor, dict):
        display_name = str(discord_actor.get("display_name") or "").strip()
        if display_name:
            return display_name
    return _assigned_display_name(event.get("actor")) or "-"


def _subject_by_id(incident: dict, subject_id: object) -> dict:
    normalized = str(subject_id or "").strip()
    if not normalized:
        return {}
    return next(
        (
            subject
            for subject in incident.get("subjects") or []
            if str(subject.get("id") or "") == normalized
        ),
        {},
    )


def _action_target(incident: dict, arguments: dict) -> object:
    if arguments.get("reporter_action") is True:
        return incident.get("reporter_name")
    subject = _subject_by_id(incident, arguments.get("subject_id"))
    if subject:
        if subject.get("kind") == "squad":
            return (
                subject.get("leader_name")
                or (subject.get("snapshot") or {}).get("leader", {}).get("name")
                or subject.get("squad_name")
                or subject.get("display_name")
            )
        return subject.get("display_name") or subject.get("player_name")
    return arguments.get("player_name") or incident.get("target_name")


def _action_timestamp(event: dict) -> str:
    value = event.get("created_at")
    if not value:
        return ""
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
        return f"<t:{int(parsed.timestamp())}:f>: "
    except (TypeError, ValueError, OverflowError):
        return ""


def _incident_log_entry(event: dict, incident: dict, language: str) -> str | None:
    event_type = str(event.get("event_type") or "")
    payload = event.get("payload") or {}
    arguments = payload.get("arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {}
    actor = _truncate(_action_actor(event, arguments), 100)
    timestamp = _action_timestamp(event)
    if event_type in {
        "claim",
        "unclaim",
        "resolved",
        "dismissed",
        "reopen",
        "reassign",
    }:
        if language == "fr":
            if event_type == "claim":
                description = f"{actor} a commencé le traitement manuel." if payload.get("mode") == "manual" else f"{actor} a pris en charge le signalement."
            elif event_type == "unclaim":
                description = f"{actor} a libéré le signalement."
            elif event_type == "resolved":
                description = f"{actor} a terminé le signalement."
            elif event_type == "dismissed":
                description = f"{actor} a clos le signalement comme visant le mauvais joueur." if payload.get("reason") == "wrong_player" else f"{actor} a rejeté le signalement comme injustifié."
            elif event_type == "reopen":
                description = f"{actor} a rouvert le signalement."
            else:
                assignee = _truncate(_assigned_display_name(payload.get("assigned_to")) or "-", 100)
                description = f"{actor} a transmis le signalement à {assignee}."
        elif language == "de":
            if event_type == "claim":
                description = (
                    f"{actor} übernahm die manuelle Bearbeitung."
                    if payload.get("mode") == "manual"
                    else f"{actor} übernahm den Report."
                )
            elif event_type == "unclaim":
                description = f"{actor} gab den Report wieder frei."
            elif event_type == "resolved":
                description = f"{actor} schloss den Report ab."
            elif event_type == "dismissed":
                description = (
                    f"{actor} schloss den Report als Fehlmeldung."
                    if payload.get("reason") == "wrong_player"
                    else f"{actor} lehnte den Report als unberechtigt ab."
                )
            elif event_type == "reopen":
                description = f"{actor} öffnete den Report erneut."
            else:
                assignee = _truncate(
                    _assigned_display_name(payload.get("assigned_to")) or "-", 100
                )
                description = f"{actor} übergab den Report an {assignee}."
        else:
            if event_type == "claim":
                description = (
                    f"{actor} started manual processing."
                    if payload.get("mode") == "manual"
                    else f"{actor} claimed the report."
                )
            elif event_type == "unclaim":
                description = f"{actor} released the report."
            elif event_type == "resolved":
                description = f"{actor} closed the report."
            elif event_type == "dismissed":
                description = (
                    f"{actor} closed the report as a wrong-player report."
                    if payload.get("reason") == "wrong_player"
                    else f"{actor} rejected the report as unjustified."
                )
            elif event_type == "reopen":
                description = f"{actor} reopened the report."
            else:
                assignee = _truncate(
                    _assigned_display_name(payload.get("assigned_to")) or "-", 100
                )
                description = f"{actor} handed the report to {assignee}."
        return _truncate(f"{timestamp}{description}", 700)
    if event_type not in {"action", "action_failed"}:
        return None
    action = str(payload.get("action") or arguments.get("action") or "").strip()
    reporter_action = arguments.get("reporter_action") is True
    target = _truncate(_action_target(incident, arguments), 100)
    reason = _truncate(arguments.get("reason"), 300)
    message = _truncate(arguments.get("message"), 300)
    duration = arguments.get("duration_hours") or arguments.get("duration")
    failed = (
        event_type == "action_failed"
        or bool(payload.get("error"))
        or payload.get("result") is False
    )
    action_result = payload.get("result")
    punish_message_fallback = (
        action == "punish"
        and isinstance(action_result, dict)
        and action_result.get("outcome")
        == "punish_not_confirmed_message_sent"
        and action_result.get("message_sent") is True
        and action_result.get("punished") is False
    )

    if punish_message_fallback:
        if language == "fr":
            description = (f"⚠️ {actor} n’a pas pu confirmer la punition de {target} ; "
                           f"le joueur était peut-être déjà mort. Le motif a été envoyé "
                           f"sous forme de message : {reason}")
        elif language == "de":
            description = (
                f"⚠️ {actor} konnte die Bestrafung von {target} nicht bestätigen. "
                f"Der Spieler war möglicherweise bereits tot. Der Grund wurde als "
                f"Nachricht gesendet: {reason}"
            )
        else:
            description = (
                f"⚠️ {actor} could not confirm the punishment for {target}; the "
                f"player may already have been dead. The reason was sent as a "
                f"message instead: {reason}"
            )
        return _truncate(f"{timestamp}{description}", 700)

    if language == "fr":
        descriptions = {
            "message": f"{actor} a envoyé un message {'au signaleur' if reporter_action else 'au joueur'} {target}. Contenu : {message}",
            "punish": f"{actor} a puni {target}. Motif : {reason}",
            "kick": f"{actor} a expulsé {target}. Motif : {reason}",
            "temp_ban": f"{actor} a banni {target} pendant {duration or '-'} heures. Motif : {reason}",
            "perma_ban": f"{actor} a banni {target} définitivement. Motif : {reason}",
            "blacklist": f"{actor} a ajouté {target} à la liste noire. Motif : {reason}",
            "remove_from_squad": f"{actor} a retiré {target} de l’escouade. Motif : {reason}",
            "disband_squad": f"{actor} a dissous l’escouade. Motif : {reason}",
        }
        description = descriptions.get(action, f"{actor} a effectué {action or 'une action'} pour {target}.")
        if failed:
            description = f"❌ Échec : {description}"
    elif language == "de":
        descriptions = {
            "message": (
                f"{actor} schrieb dem {'Melder' if reporter_action else 'Spieler'} "
                f"{target} eine Nachricht. Inhalt: {message}"
            ),
            "punish": f"{actor} bestrafte {target}. Grund: {reason}",
            "kick": f"{actor} kickte {target}. Grund: {reason}",
            "temp_ban": (
                f"{actor} bannte {target} für {duration or '-'} Stunden. Grund: {reason}"
            ),
            "perma_ban": f"{actor} bannte {target} permanent. Grund: {reason}",
            "blacklist": f"{actor} setzte {target} auf die Blacklist. Grund: {reason}",
            "remove_from_squad": (
                f"{actor} entfernte {target} aus dem Squad. Grund: {reason}"
            ),
            "disband_squad": f"{actor} löste den Squad auf. Grund: {reason}",
        }
        description = descriptions.get(
            action, f"{actor} führte {action or 'eine Aktion'} für {target} aus."
        )
        if failed:
            description = f"❌ Fehlgeschlagen: {description}"
    else:
        descriptions = {
            "message": (
                f"{actor} sent a message to the {'reporter' if reporter_action else 'player'} "
                f"{target}. Content: {message}"
            ),
            "punish": f"{actor} punished {target}. Reason: {reason}",
            "kick": f"{actor} kicked {target}. Reason: {reason}",
            "temp_ban": (
                f"{actor} banned {target} for {duration or '-'} hours. Reason: {reason}"
            ),
            "perma_ban": f"{actor} permanently banned {target}. Reason: {reason}",
            "blacklist": f"{actor} added {target} to the blacklist. Reason: {reason}",
            "remove_from_squad": (
                f"{actor} removed {target} from the squad. Reason: {reason}"
            ),
            "disband_squad": f"{actor} disbanded the squad. Reason: {reason}",
        }
        description = descriptions.get(
            action, f"{actor} performed {action or 'an action'} for {target}."
        )
        if failed:
            description = f"❌ Failed: {description}"
    return _truncate(f"{timestamp}{description}", 700)


def _action_log_field(incident: dict, language: str) -> dict | None:
    entries = [
        entry
        for event in incident.get("events") or []
        if (entry := _incident_log_entry(event, incident, language))
    ]
    if not entries:
        return None
    # Discord limits one embed field to 1024 characters. Keep the newest
    # actions, but retain their chronological order inside the logbook.
    while len("\n".join(entries)) > 1024 and len(entries) > 1:
        entries.pop(0)
    return {
        "name": "Logbuch" if language == "de" else "Journal" if language == "fr" else "Logbook",
        "value": _truncate("\n".join(entries), 1024),
        "inline": False,
    }


def _squad_leader(snapshot: dict) -> dict:
    leader = snapshot.get("leader") or {}
    if leader:
        return leader
    for player in snapshot.get("players") or []:
        role = "".join(
            character
            for character in str(player.get("role") or "").casefold()
            if character.isalnum()
        )
        if role in SQUAD_LEADER_ROLES:
            return player
    return {}


def _display_unit(value: object) -> str:
    text = str(value or "-").strip() or "-"
    return text.title() if text.islower() or text.isupper() else text


def _confirmed_squad_subjects(incident: dict) -> list[dict]:
    return [
        subject
        for subject in incident.get("subjects") or []
        if subject.get("kind") == "squad" and subject.get("state") == "confirmed"
    ]


def _additional_squad_embed(
    subject: dict,
    *,
    envelope: IncidentEventEnvelope,
    incident: dict,
    language: str,
    selected: bool,
    position: int,
    total: int,
) -> dict:
    snapshot = subject.get("snapshot") or {}
    leader = _squad_leader(snapshot)
    team = subject.get("team") or snapshot.get("team")
    team_emoji, color = _team_style(team, None)
    squad_name = _display_unit(subject.get("squad_name") or subject.get("display_name"))
    leader_name = subject.get("leader_name") or leader.get("name") or "-"
    player_id = subject.get("leader_player_id") or leader.get("player_id")
    identity = f"👤 **{_truncate(leader_name, 200)}**"
    if _present(leader.get("level")):
        identity += f" (Lvl {leader['level']})"
    if player_id:
        identity += f"\n🆔 `{_truncate(player_id, 100)}`"

    fields = [
        {
            "name": "📣 Grund der Meldung" if language == "de" else "📣 Motif du signalement" if language == "fr" else "📣 Report reason",
            "value": _truncate(incident.get("reason"), 1024),
            "inline": False,
        },
        *_player_stat_fields(leader, language, leader=True),
    ]
    members = snapshot.get("players") or []
    if members:
        member_lines = []
        for member in members:
            entry = (
                f"{member.get('name') or '-'} (Lvl {member.get('level') if member.get('level') is not None else '–'})"
                f" • {member.get('kills') if member.get('kills') is not None else '–'}/{member.get('deaths') if member.get('deaths') is not None else '–'}"
                f" • {member.get('role') or '-'}"
            )
            if str(member.get("player_id") or "") == str(player_id or ""):
                entry = f"**{entry}**"
            member_lines.append(entry)
        fields.append(
            {
                "name": f"👥 {'Membres de l’escouade' if language == 'fr' else 'Squad Members'} ({len(member_lines)})",
                "value": _truncate("\n".join(member_lines), 1024),
                "inline": False,
            }
        )
    game_label = "HLL Vietnam" if envelope.game == "hll_vietnam" else "Hell Let Loose"
    marker = "🎯 " if selected else ""
    return {
        "title": _truncate(
            f"{marker}{team_emoji} {squad_name} | {_display_unit(team)}", 256
        ),
        "description": _truncate(identity, 4096),
        "color": color,
        "fields": fields[:25],
        "footer": {
            "text": _truncate(
                f"Squad {position}/{total} | {envelope.server_name} · "
                f"#{envelope.server_number} · {game_label}",
                2048,
            )
        },
    }


def render_message(
    envelope: IncidentEventEnvelope,
    analysis: ModerationAnalysis | None,
    *,
    ai_unavailable: bool = False,
    selected_subject_id: str | None = None,
) -> dict:
    incident = envelope.incident
    primary = incident.get("primary_subject") or {}
    squad_subjects = _confirmed_squad_subjects(incident)
    multi_squad_report = (
        str(incident.get("source") or "") in {"chat", "manual"}
        and len(squad_subjects) > 1
    )
    selected_squad = next(
        (
            subject
            for subject in squad_subjects
            if str(subject.get("id") or "") == str(selected_subject_id or "")
        ),
        None,
    )
    if selected_squad:
        primary = selected_squad
    language = incident.get("discord_language", "de")
    if not isinstance(language, str) or language not in {"de", "en", "fr"}:
        language = "de"
    labels = {
        "de": {
            "report_title": "Bericht für Spieler: {name}",
            "name_title": "KI-Namensprüfung: {name}",
            "chat_title": "KI-Chatprüfung: {name}",
            "check_match": "Bitte überprüfen, ob der Report zur Spielermeldung passt.",
            "reason": "📣 Grund der Meldung",
            "reporter": "☎️ Melder",
            "dismiss": "🙄 Ablehnen",
            "trash": "🗑 Papierkorb",
            "manual": "👀 Manuell bearbeiten",
            "finish": "✅ Bearbeitung abschließen",
            "not_configured": "⚙️ Keine Moderatorrolle eingerichtet. Aktionen sind gesperrt.",
            "unavailable": "Nicht verfügbar",
            "unresolved_target": "Kein eindeutiger Zielspieler",
            "unresolved_target_note": "Kein eindeutiger Zielspieler erkannt. Moderationsaktionen sind gesperrt.",
        },
        "en": {
            "report_title": "Report for player: {name}",
            "name_title": "AI name review: {name}",
            "chat_title": "AI chat review: {name}",
            "check_match": "Please check if the report matches the player report.",
            "reason": "📣 Report reason",
            "reporter": "☎️ Reporter",
            "dismiss": "❎ Unjustified",
            "trash": "🗑 Trash",
            "manual": "👀 Process manually",
            "finish": "✅ Finish processing",
            "not_configured": "⚙️ No moderator role configured. Actions are locked.",
            "unavailable": "Unavailable",
            "unresolved_target": "No unambiguous reported player",
            "unresolved_target_note": "No unambiguous reported player was found. Moderation actions are locked.",
        },
        "fr": {
            "report_title": "Signalement du joueur : {name}", "name_title": "Examen du nom par IA : {name}",
            "chat_title": "Examen du chat par IA : {name}", "check_match": "Vérifiez que le dossier correspond au signalement du joueur.",
            "reason": "📣 Motif du signalement", "reporter": "☎️ Signaleur", "dismiss": "❎ Non justifié",
            "trash": "🗑 Corbeille", "manual": "👀 Traiter manuellement", "finish": "✅ Terminer le traitement",
            "not_configured": "⚙️ Aucun rôle de modérateur configuré. Les actions sont bloquées.", "unavailable": "Indisponible",
            "unresolved_target": "Aucun joueur signalé identifié sans ambiguïté",
            "unresolved_target_note": "Aucun joueur signalé n’a été identifié sans ambiguïté. Les actions de modération sont bloquées.",
        },
    }.get(language, {})
    source = str(incident.get("source") or "manual")
    targetless_report = (
        source in {"chat", "manual"} and not primary and not incident.get("target_id")
    )
    snapshot = primary.get("snapshot") or {}
    is_squad_report = primary.get("kind") == "squad"
    stat_snapshot = _squad_leader(snapshot) if is_squad_report else snapshot
    target_online = stat_snapshot.get("online") is not False
    team = primary.get("team") or snapshot.get("team")
    target_name = (
        labels["unresolved_target"]
        if targetless_report
        else (
            (
                primary.get("leader_name") or stat_snapshot.get("name")
                if is_squad_report
                else primary.get("display_name")
            )
            or incident.get("target_name")
            or "-"
        )
    )
    player_id = (
        primary.get("player_id")
        or primary.get("leader_player_id")
        or stat_snapshot.get("player_id")
        or incident.get("target_id")
    )
    game_label = "HLL Vietnam" if envelope.game == "hll_vietnam" else "Hell Let Loose"
    team_emoji, color = _team_style(team, analysis.risk_score if analysis else None)
    if source == "ai_player_name":
        team_emoji = "🔎"
    status = str(incident.get("status") or "new")
    assigned_name = _assigned_display_name(incident.get("assigned_to"))
    if assigned_name and status in {"claimed", "resolved", "dismissed"}:
        color = 0x2ECC71
    identity = (
        f"⚠️ **{labels['unresolved_target_note']}**"
        if targetless_report
        else f"👤 **{_truncate(target_name, 200)}**"
    )
    if is_squad_report and _present(stat_snapshot.get("level")):
        identity += f" (Lvl {stat_snapshot['level']})"
    if player_id:
        identity += f"\n🆔 `{_truncate(player_id, 100)}`"
    unit_name = primary.get("squad_name") or stat_snapshot.get("unit_name")
    if not is_squad_report and _present(unit_name):
        identity += f"\n👥 **{_display_unit(unit_name)}**"
    if not target_online:
        identity += "\n🔴 **Hors ligne**" if language == "fr" else "\n🔴 **Offline**"
    if source in {"chat", "manual"}:
        identity += f"\n\nℹ️ *{labels['check_match']}*"
    fields = []
    if source in {"chat", "manual"}:
        fields.append(
            {
                "name": labels["reason"],
                "value": _truncate(incident.get("reason"), 1024),
                "inline": False,
            }
        )
        if targetless_report:
            fields.append(_reporter_context_field(incident, language))
        elif is_squad_report:
            fields.extend(_player_stat_fields(stat_snapshot, language, leader=True))
            members = snapshot.get("players") or []
            if members:
                member_lines = []
                for member in members:
                    entry = (
                        f"{member.get('name') or '-'} (Lvl {member.get('level') if member.get('level') is not None else '–'})"
                        f" • {member.get('kills') if member.get('kills') is not None else '–'}/{member.get('deaths') if member.get('deaths') is not None else '–'}"
                        f" • {member.get('role') or '-'}"
                    )
                    if str(member.get("player_id") or "") == str(player_id or ""):
                        entry = f"**{entry}**"
                    member_lines.append(entry)
                fields.append(
                    {
                        "name": f"👥 {'Membres de l’escouade' if language == 'fr' else 'Squad Members'} ({len(member_lines)})",
                        "value": _truncate("\n".join(member_lines), 1024),
                        "inline": False,
                    }
                )
        else:
            fields.extend(_player_stat_fields(stat_snapshot, language))
            recent_teamkill = stat_snapshot.get("recent_teamkill")
            if isinstance(recent_teamkill, dict):
                victim = recent_teamkill.get("victim_name") or "-"
                weapon = recent_teamkill.get("weapon") or "-"
                seconds = recent_teamkill.get("seconds_before_report")
                timing = (
                    f"{seconds} Sekunden vor dem Report"
                    if language == "de" and _present(seconds)
                    else f"{seconds} secondes avant le signalement" if language == "fr" and _present(seconds)
                    else (
                        f"{seconds} seconds before the report"
                        if _present(seconds)
                        else "-"
                    )
                )
                fields.append(
                    {
                        "name": (
                            "🧾 Passender Teamkill im Serverlog"
                            if language == "de"
                            else "🧾 Teamkill correspondant dans le journal du serveur" if language == "fr"
                            else "🧾 Matching teamkill in server log"
                        ),
                        "value": _truncate(
                            f"{target_name} → {victim}\n{weapon} · {timing}", 1024
                        ),
                        "inline": False,
                    }
                )
    elif analysis and source in {"ai_player_name", "ai_chat"}:
        categories = ", ".join(analysis.categories) or "-"
        fields.extend(
            [
                {
                    "name": labels["reason"],
                    "value": _truncate(incident.get("reason"), 1024),
                    "inline": False,
                },
                {
                    "name": (
                        "🤖 KI-Einschätzung" if language == "de" else "🤖 Analyse IA" if language == "fr" else "🤖 AI assessment"
                    ),
                    "value": _truncate(
                        f"**{'Risque' if language == 'fr' else 'Risiko'}:** {analysis.risk_score:.0%}\n"
                        f"**{'Catégorie' if language == 'fr' else 'Kategorie'}:** {categories}\n{analysis.rationale}",
                        1024,
                    ),
                    "inline": False,
                },
            ]
        )
    elif ai_unavailable and source in {"ai_chat", "ai_player_name"}:
        fields.append(
            {"name": "KI / AI", "value": labels["unavailable"], "inline": False}
        )
    action_log = _action_log_field(incident, language)
    report_admin = incident.get("report_admin")
    automatic_kick = (
        isinstance(report_admin, dict)
        and report_admin.get("status") == "kicked"
        and report_admin.get("mode") == "active"
        and status == "resolved"
        and incident.get("assigned_to") == "system:report-admin"
    )
    if isinstance(report_admin, dict):
        states = {
            "classifying": "KI liest vollständigen Meldegrund / AI reading complete report",
            "queued": "Prüfung ausstehend / Awaiting checks",
            "waiting": "Stille Prüffrist läuft / Silent observation window",
            "sending": "Kick wird ausgeführt / Kick in progress",
            "kicked": "Kick bestätigt / Kick confirmed",
            "dry_run": "Probelauf: kein Kick / Dry run: no kick",
            "manual": "Admins übernehmen / Manual review required",
            "unknown": "Ergebnis unklar, keine Wiederholung / Uncertain result, no retry",
        }
        if language == "fr":
            states = {
                "classifying": "L’IA lit le motif complet du signalement",
                "queued": "Vérifications en attente", "waiting": "Délai d’observation silencieuse en cours",
                "sending": "Expulsion en cours", "kicked": "Expulsion confirmée",
                "dry_run": "Simulation : aucune expulsion", "manual": "Examen manuel requis",
                "unknown": "Résultat incertain, aucune nouvelle tentative",
            }
        evidence = (
            f"{report_admin.get('teamkill_count', '–')} Teamkills · {report_admin.get('window_seconds', 0)} s Kontext / context"
            if report_admin.get("rule") == "teamkills" else
            "Cheatmeldung: Prüfung, keine automatische Sanktion / Cheat report: review only, no automatic sanction"
            if report_admin.get("rule") == "cheating" else
            "Kommunikation gemeldet; kein Sprachnachweis / Communication reported; no voice evidence"
            if report_admin.get("rule") == "communication" else
            "Meldegrund noch keiner freigegebenen Regel zugeordnet / Report not yet assigned to an approved rule"
        )
        if language == "fr":
            if report_admin.get("rule") == "teamkills":
                evidence = f"{report_admin.get('teamkill_count', '–')} teamkills · {report_admin.get('window_seconds', 0)} s de contexte"
            elif report_admin.get("rule") == "cheating":
                evidence = "Signalement de triche : examen uniquement, aucune sanction automatique"
            elif report_admin.get("rule") == "communication":
                evidence = "Communication signalée ; aucune preuve de l’activité vocale"
            else:
                evidence = "Motif pas encore associé à une règle approuvée"
        admin_field = {
            "name": "🤖 Report-Admin",
            "value": _truncate(
                f"{states.get(report_admin.get('status'), 'Examen manuel' if language == 'fr' else 'Manual review')}\n"
                f"{report_admin.get('target_name') or '-'}\n{evidence}\n"
                f"{report_admin.get('result') or ''}\n{report_admin.get('sent_reason') or ''}", 1024),
            "inline": False,
        }
        if automatic_kick:
            reason = report_admin.get("sent_reason") or report_admin.get("result") or "–"
            kicked_name = report_admin.get("target_name") or target_name
            admin_field.update(
                name=("✅ Automatischer Eingriff – Report-Admin" if language == "de" else "✅ Intervention automatique – administration des signalements" if language == "fr" else "✅ Automatic action – report admin"),
                value=_truncate(
                    (f"**Aktion:** Server-Kick bestätigt\n**Spieler:** {kicked_name}\n**Grund:** {reason}" if language == "de" else
                     f"**Action :** expulsion du serveur confirmée\n**Joueur :** {kicked_name}\n**Motif :** {reason}" if language == "fr" else
                     f"**Action:** Server kick confirmed\n**Player:** {kicked_name}\n**Reason:** {reason}")
                    + "\n" + evidence, 1024),
            )
            fields.insert(0, admin_field)
            color = 0x2ECC71
        else:
            fields.append(admin_field)
        if report_admin.get("status") == "waiting" and isinstance(report_admin.get("ready_at"), (int, float)):
            admin_field["value"] = _truncate(admin_field["value"] + f"\n<t:{int(report_admin['ready_at'])}:R>", 1024)
        fields.extend(case_fields(report_admin, language))
    vote = incident.get("leadership_vote")
    if vote:
        deadline = f"<t:{int(vote['ends_at'])}:R>" if vote.get("ends_at") and vote.get("status") in {"confirming", "warning", "active", "inviting"} else "–"
        roster = vote.get("electorate") or {}
        ballots = vote.get("ballots") or {}
        lines = [f"{roster.get(pid, {}).get('name') or pid}: {('Oui' if b['yes'] else 'Non') if language == 'fr' else ('Ja / Yes' if b['yes'] else 'Nein / No')}" for pid, b in ballots.items()]
        target_role = "Commander" if vote.get("target_role") == "commander" else f"Squad {vote.get('squad')} – Squadleader"
        mode = "PROBELAUF / DRY RUN – kein Kick / no kick" if vote.get("mode") != "active" else "AKTIV / ACTIVE – Server-Kick"
        phases = {
            "confirming": "Bestätigung / Confirmation", "warning": "Warnfrist / Warning",
            "inviting": "Einladungen / Invitations", "active": "Abstimmung / Voting",
            "executing": "Kick-Prüfung / Execution", "kicked": "Kick bestätigt / Confirmed",
            "dry_run": "Probelauf erfolgreich – manuell bearbeiten / Dry run passed – manual review",
            "rejected": "Mehrheit fehlt – Admins erforderlich / No majority – admins needed",
            "cancelled": "Abgebrochen – Admins erforderlich / Cancelled – admins needed",
            "unknown": "Unklar – keine Wiederholung / Uncertain – no retry",
        }
        if language == "fr":
            mode = "SIMULATION – aucune expulsion" if vote.get("mode") != "active" else "ACTIF – expulsion du serveur"
            target_role = "Commandant" if vote.get("target_role") == "commander" else f"Escouade {vote.get('squad')} – chef d’escouade"
            phases = {
                "confirming": "Confirmation", "warning": "Avertissement", "inviting": "Invitations", "active": "Vote en cours", "executing": "Exécution", "kicked": "Expulsion confirmée", "dry_run": "Simulation réussie – examen manuel", "rejected": "Pas de majorité – administrateurs requis", "cancelled": "Annulé – administrateurs requis", "unknown": "Résultat incertain – aucune nouvelle tentative",
            }
        fields.append({"name": "🗳 Führungsabstimmung" if language == "de" else "🗳 Vote de commandement" if language == "fr" else "🗳 Leadership vote",
            "value": _truncate(f"{mode}\n{target_role} {vote.get('target_name')}\n{phases.get(vote.get('status'), vote.get('status'))} · {deadline}\n"
                f"{'Oui' if language == 'fr' else 'Ja / Yes'}: {vote.get('yes', 0)} · {'Non' if language == 'fr' else 'Nein / No'}: {vote.get('no', 0)} · ≥ {vote.get('required') or '–'} / {vote.get('participant_count', len(roster))}\n"
                f"{vote.get('result') or ''}\n" + "\n".join(lines), 1024), "inline": False})
    if action_log:
        fields.append(action_log)
    if multi_squad_report:
        selected_label = (
            _display_unit(
                selected_squad.get("squad_name") or selected_squad.get("display_name")
            )
            if selected_squad
            else None
        )
        fields.append(
            {
                "name": "🎯 Zielauswahl" if language == "de" else "🎯 Sélection de la cible" if language == "fr" else "🎯 Target selection",
                "value": (
                    f"Ausgewählt: **{selected_label}**"
                    if selected_label and language == "de"
                    else f"Sélection : **{selected_label}**" if selected_label and language == "fr"
                    else (
                        f"Selected: **{selected_label}**"
                        if selected_label
                        else (
                            "Bitte vor einer Aktion unten ein Squad auswählen."
                            if language == "de"
                            else "Sélectionnez une escouade ci-dessous avant toute action." if language == "fr"
                            else "Select a squad below before running an action."
                        )
                    )
                ),
                "inline": False,
            }
        )
    revision = envelope.incident_revision
    incident_id = envelope.incident_id
    allowed_actions = [
        action
        for action in incident.get("allowed_actions") or []
        if action
        in {
            "message",
            "punish",
            "kick",
            "temp_ban",
            "perma_ban",
            "blacklist",
            "remove_from_squad",
            "disband_squad",
        }
    ]
    components = []
    moderation_ready = incident.get("discord_moderation_ready", True)
    has_player_target = bool(player_id)
    has_squad_target = bool(
        team and primary.get("squad_name")
    )
    if status in {"resolved", "dismissed"}:
        pass
    elif not moderation_ready:
        fields.append(
            {"name": "Discord", "value": labels["not_configured"], "inline": False}
        )
    else:
        if multi_squad_report:
            components.append(
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": f"subject:{incident_id}:{revision}",
                            "placeholder": (
                                "Squad für die Aktion auswählen"
                                if language == "de"
                                else "Sélectionner l’escouade pour l’action" if language == "fr"
                                else "Select squad for the action"
                            ),
                            "min_values": 1,
                            "max_values": 1,
                            "options": [
                                {
                                    "label": _truncate(
                                        _display_unit(
                                            subject.get("squad_name")
                                            or subject.get("display_name")
                                        ),
                                        100,
                                    ),
                                    "value": str(subject.get("id")),
                                    "description": _truncate(
                                        f"{_display_unit(subject.get('team'))} · "
                                        f"{subject.get('leader_name') or ('Aucun chef d’escouade' if language == 'fr' else 'Kein Squadlead')}",
                                        100,
                                    ),
                                    "default": str(subject.get("id") or "")
                                    == str(selected_subject_id or ""),
                                }
                                for subject in squad_subjects[:25]
                                if subject.get("id")
                            ],
                        }
                    ],
                }
            )
        if _manual_processing(incident):
            components.append(
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 3,
                            "label": labels["finish"],
                            "custom_id": f"finish:{incident_id}:{revision}",
                        }
                    ],
                }
            )
        else:
            old_actions = [
                (
                    "message",
                    2,
                    (
                        "📧 Nachricht"
                        if multi_squad_report and language == "de"
                        else (
                            "📧 Message"
                            if multi_squad_report
                            else f"📧 {_truncate(target_name, 65)}"
                        )
                    ),
                ),
                ("punish", 1, "💀 Bestrafen" if language == "de" else "💀 Punir" if language == "fr" else "💀 Punish"),
                ("kick", 3, "🤜 Kicken" if language == "de" else "🤜 Expulser" if language == "fr" else "🤜 Kick"),
                ("temp_ban", 3, "⏰ TB"),
                ("perma_ban", 4, "🔨 PB"),
            ]
            row = [
                {
                    "type": 2,
                    "style": style,
                    "label": label,
                    "custom_id": f"action:{incident_id}:{revision}:{action}",
                }
                for action, style, label in old_actions
                if has_player_target
                and action in allowed_actions
                and (target_online or action in {"temp_ban", "perma_ban"})
            ]
            if row:
                components.append({"type": 1, "components": row})
            context_row = []
            if incident.get("reporter_id") and "message" in allowed_actions:
                context_row.append(
                    {
                        "type": 2,
                        "style": 2,
                        "label": labels["reporter"],
                        "custom_id": f"action:{incident_id}:{revision}:message_reporter",
                    }
                )
            if has_player_target and "blacklist" in allowed_actions:
                context_row.append(
                    {
                        "type": 2,
                        "style": 4,
                        "label": "⛔ Liste noire" if language == "fr" else "⛔ Blacklist",
                        "custom_id": f"action:{incident_id}:{revision}:blacklist",
                    }
                )
            for action, style, label in [
                ("remove_from_squad", 1, "🥾 Expulser de l’escouade" if language == "fr" else "🥾 Squad Kick"),
                (
                    "disband_squad",
                    4,
                    "💣 Squad auflösen" if language == "de" else "💣 Dissoudre l’escouade" if language == "fr" else "💣 Disband squad",
                ),
            ]:
                if (
                    has_squad_target if action == "disband_squad" else has_player_target
                ) and action in allowed_actions and target_online:
                    context_row.append(
                        {
                            "type": 2,
                            "style": style,
                            "label": label,
                            "custom_id": f"action:{incident_id}:{revision}:{action}",
                        }
                    )
            if has_player_target:
                context_row.append(
                    {
                        "type": 2,
                        "style": 2,
                        "label": "📄 Journaux" if language == "fr" else "📄 Logs",
                        "custom_id": f"logs:{incident_id}:{revision}",
                    }
                )
            if context_row:
                components.append({"type": 1, "components": context_row[:5]})
            components.append(
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 2,
                            "label": labels["dismiss"],
                            "custom_id": f"dismiss:{incident_id}:{revision}",
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "label": labels["trash"],
                            "custom_id": f"trash:{incident_id}:{revision}",
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "label": labels["manual"],
                            "custom_id": f"manual:{incident_id}:{revision}",
                        },
                    ],
                }
            )
    if vote and vote.get("status") in {"confirming", "warning", "inviting", "active", "executing"} and moderation_ready and status not in {"resolved", "dismissed"}:
        button = {"type": 2, "style": 2, "label": "Vote abbrechen" if language == "de" else "Annuler le vote" if language == "fr" else "Cancel vote",
                  "custom_id": f"cancel_leadership_vote:{incident_id}:{revision}"}
        # Keep Discord's maximum five action rows / five buttons per row.
        button_row = next((row for row in reversed(components) if len(row["components"]) < 5 and all(c["type"] == 2 for c in row["components"])), None)
        if button_row:
            button_row["components"].append(button)
        elif len(components) < 5:
            components.append({"type": 1, "components": [button]})
    if source == "ai_player_name":
        title = labels["name_title"].format(name=target_name)
    elif source == "ai_chat":
        title = labels["chat_title"].format(name=target_name)
    elif is_squad_report and source in {"chat", "manual"}:
        title = (
            f"{_display_unit(primary.get('squad_name') or primary.get('display_name'))}"
            f" | {_display_unit(team)}"
        )
    else:
        title = labels["report_title"].format(name=target_name)
    if automatic_kick:
        title = ("Automatisch gekickt – " if language == "de" else "Expulsion automatique – " if language == "fr" else "Automatically kicked – ") + str(report_admin.get("target_name") or target_name)
        team_emoji = "🤖"
    footer_parts = []
    if automatic_kick:
        footer_parts.append("Automatisch bearbeitet durch Report-Admin" if language == "de" else "Traité automatiquement par l’administration des signalements" if language == "fr" else "Automatically handled by report admin")
    elif assigned_name:
        footer_parts.append(
            ("Bearbeitet von " if language == "de" else "Traité par " if language == "fr" else "Handled by ") + assigned_name
        )
    footer_parts.extend(
        [
            "HLL Unit Report" if is_squad_report else "HLL Player Report",
            f"{envelope.server_name} · #{envelope.server_number} · {game_label}",
        ]
    )
    primary_embed = {
        "title": _truncate(f"{team_emoji} {title}", 256),
        "description": _truncate(identity, 4096),
        "color": color,
        "fields": fields[:25],
        "footer": {"text": _truncate(" | ".join(footer_parts), 2048)},
    }
    embeds = [primary_embed]
    if multi_squad_report:
        ordered_subjects = [
            subject
            for subject in squad_subjects
            if str(subject.get("id") or "") != str(primary.get("id") or "")
        ]
        for position, subject in enumerate(ordered_subjects[:9], start=2):
            embeds.append(
                _additional_squad_embed(
                    subject,
                    envelope=envelope,
                    incident=incident,
                    language=language,
                    selected=str(subject.get("id") or "")
                    == str(selected_subject_id or ""),
                    position=position,
                    total=len(squad_subjects),
                )
            )
    return {
        "embeds": _bounded_report_embeds(embeds, language),
        "components": components,
        "allowed_mentions": {"parse": []},
    }


class DiscordClient:
    def __init__(self, settings: Settings | None = None, client=None):
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(timeout=10)

    def validate_channel(self, channel_id: str, guild_id: str) -> None:
        if self.settings.dry_run or not self.settings.discord_bot_token:
            return
        response = self.client.get(
            f"https://discord.com/api/v10/channels/{channel_id}",
            headers={"Authorization": f"Bot {self.settings.discord_bot_token}"},
        )
        response.raise_for_status()
        if str(response.json().get("guild_id") or "") != guild_id:
            raise ValueError("Discord channel does not belong to the selected guild")

    def single_guild_options(self, preferred_guild_id: str | None = None) -> dict:
        """Return the bot's only guild and its selectable channels and roles.

        Guild selection is deliberately not delegated to CRCON clients.  A
        single-guild installation has one authoritative Discord binding; if the
        bot is installed elsewhere too, pairing must stop instead of guessing.
        """

        if self.settings.dry_run or not self.settings.discord_bot_token:
            return self.guild_options("123")
        response = self.client.get(
            "https://discord.com/api/v10/users/@me/guilds",
            headers={"Authorization": f"Bot {self.settings.discord_bot_token}"},
        )
        response.raise_for_status()
        guilds = response.json()
        if not isinstance(guilds, list):
            raise ValueError("Discord returned an invalid guild list")
        if not guilds:
            raise ValueError("The Discord app is not installed on a server")
        if len(guilds) == 1:
            guild_id = str(guilds[0].get("id") or "")
        elif preferred_guild_id and any(
            str(item.get("id") or "") == preferred_guild_id for item in guilds
        ):
            # An already completed CRCON pairing is a trusted server-side
            # binding. It is safer than accepting a guild ID from the browser.
            guild_id = preferred_guild_id
        else:
            raise ValueError(
                "The Discord app is installed on more than one server; "
                "automatic guild selection is ambiguous"
            )
        if not guild_id:
            raise ValueError("Discord returned a guild without an ID")
        return self.guild_options(guild_id)

    def guild_options(self, guild_id: str) -> dict:
        if self.settings.dry_run or not self.settings.discord_bot_token:
            return {
                "guild": {"id": guild_id, "name": guild_id},
                "channels": [],
                "roles": [],
            }
        headers = {"Authorization": f"Bot {self.settings.discord_bot_token}"}
        guild_response = self.client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}", headers=headers
        )
        channels_response = self.client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers
        )
        roles_response = self.client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=headers
        )
        guild_response.raise_for_status()
        channels_response.raise_for_status()
        roles_response.raise_for_status()
        guild = guild_response.json()
        channels = sorted(
            (
                {
                    "id": str(item["id"]),
                    "name": str(item.get("name") or item["id"]),
                    "position": int(item.get("position") or 0),
                }
                for item in channels_response.json()
                if item.get("type") in {0, 5}
            ),
            key=lambda item: (item["position"], item["name"].casefold()),
        )
        roles = sorted(
            (
                {
                    "id": str(item["id"]),
                    "name": str(item.get("name") or item["id"]),
                    "position": int(item.get("position") or 0),
                }
                for item in roles_response.json()
                if not item.get("managed") and item.get("name") != "@everyone"
            ),
            key=lambda item: (-item["position"], item["name"].casefold()),
        )
        return {
            "guild": {
                "id": str(guild["id"]),
                "name": str(guild.get("name") or guild["id"]),
            },
            "channels": channels,
            "roles": roles,
        }

    def upsert(
        self, channel_id: str, payload: dict, message_id: str | None = None
    ) -> str:
        if self.settings.dry_run or not self.settings.discord_bot_token:
            identity = (
                message_id
                or hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:18]
            )
            return identity
        headers = {"Authorization": f"Bot {self.settings.discord_bot_token}"}
        if message_id:
            response = self.client.patch(
                f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
                headers=headers,
                json=payload,
            )
        else:
            response = self.client.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        return str(response.json()["id"])
