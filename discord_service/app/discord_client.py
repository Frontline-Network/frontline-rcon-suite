from __future__ import annotations

import hashlib
from datetime import datetime

import httpx

from .config import Settings, get_settings
from .contracts import IncidentEventEnvelope, ModerationAnalysis

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


def _action_timestamp(event: dict) -> str:
    value = event.get("created_at")
    if not value:
        return ""
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        return f"<t:{int(parsed.timestamp())}:f>: "
    except (TypeError, ValueError, OverflowError):
        return ""


def _action_log_entry(event: dict, incident: dict, language: str) -> str | None:
    event_type = str(event.get("event_type") or "")
    if event_type not in {"action", "action_failed"}:
        return None
    payload = event.get("payload") or {}
    arguments = payload.get("arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {}
    action = str(payload.get("action") or arguments.get("action") or "").strip()
    actor = _truncate(_action_actor(event, arguments), 100)
    reporter_action = arguments.get("reporter_action") is True
    target = _truncate(
        (
            incident.get("reporter_name")
            if reporter_action
            else arguments.get("player_name") or incident.get("target_name")
        ),
        100,
    )
    reason = _truncate(arguments.get("reason"), 300)
    message = _truncate(arguments.get("message"), 300)
    duration = arguments.get("duration_hours") or arguments.get("duration")
    failed = (
        event_type == "action_failed"
        or bool(payload.get("error"))
        or payload.get("result") is False
    )

    if language == "de":
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
    return _truncate(f"{_action_timestamp(event)}{description}", 700)


def _action_log_field(incident: dict, language: str) -> dict | None:
    entries = [
        entry
        for event in incident.get("events") or []
        if (entry := _action_log_entry(event, incident, language))
    ]
    if not entries:
        return None
    # Discord limits one embed field to 1024 characters. Keep the newest
    # actions, but retain their chronological order inside the logbook.
    while len("\n".join(entries)) > 1024 and len(entries) > 1:
        entries.pop(0)
    return {
        "name": "Logbuch" if language == "de" else "Logbook",
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


def render_message(
    envelope: IncidentEventEnvelope,
    analysis: ModerationAnalysis | None,
    *,
    ai_unavailable: bool = False,
) -> dict:
    incident = envelope.incident
    primary = incident.get("primary_subject") or {}
    language = incident.get("discord_language", "de")
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
        },
    }.get(language, {})
    snapshot = primary.get("snapshot") or {}
    is_squad_report = primary.get("kind") == "squad"
    stat_snapshot = _squad_leader(snapshot) if is_squad_report else snapshot
    team = primary.get("team") or snapshot.get("team")
    target_name = (
        primary.get("leader_name") or stat_snapshot.get("name")
        if is_squad_report
        else primary.get("display_name")
    ) or incident.get("target_name") or "-"
    player_id = (
        primary.get("player_id")
        or primary.get("leader_player_id")
        or stat_snapshot.get("player_id")
        or incident.get("target_id")
    )
    kills = stat_snapshot.get("kills")
    deaths = stat_snapshot.get("deaths")
    kd = None
    if isinstance(kills, (int, float)) and isinstance(deaths, (int, float)):
        kd = f"{kills / max(deaths, 1):.2f}"
    playtime_seconds = stat_snapshot.get("map_playtime_seconds")
    playtime_hours = (
        float(playtime_seconds) / 3600
        if isinstance(playtime_seconds, (int, float))
        else None
    )
    kpm = (
        float(kills) / max(float(playtime_seconds) / 60, 1)
        if isinstance(kills, (int, float))
        and isinstance(playtime_seconds, (int, float))
        else None
    )
    game_label = "HLL Vietnam" if envelope.game == "hll_vietnam" else "Hell Let Loose"
    source = str(incident.get("source") or "manual")
    team_emoji, color = _team_style(team, analysis.risk_score if analysis else None)
    if source == "ai_player_name":
        team_emoji = "🔎"
    status = str(incident.get("status") or "new")
    assigned_name = _assigned_display_name(incident.get("assigned_to"))
    if assigned_name and status in {"claimed", "resolved", "dismissed"}:
        color = 0x2ECC71
    identity = f"👤 **{_truncate(target_name, 200)}**"
    if is_squad_report and _present(stat_snapshot.get("level")):
        identity += f" (Lvl {stat_snapshot['level']})"
    if player_id:
        identity += f"\n🆔 `{_truncate(player_id, 100)}`"
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
        if is_squad_report:
            fields.extend(
                [
                    {
                        "name": "⚔️ Kills",
                        "value": f"**{kills if _present(kills) else '-'}**",
                        "inline": True,
                    },
                    {
                        "name": "💀 Deaths",
                        "value": f"**{deaths if _present(deaths) else '-'}**",
                        "inline": True,
                    },
                    {
                        "name": "⏱️ Gesamtspielzeit" if language == "de" else "⏱️ Total playtime",
                        "value": (
                            f"{playtime_hours:.1f} h"
                            if playtime_hours is not None
                            else "-"
                        ),
                        "inline": True,
                    },
                ]
            )
            members = snapshot.get("players") or []
            if members:
                member_lines = []
                for member in members:
                    entry = (
                        f"{member.get('name') or '-'} (Lvl {member.get('level') or 0})"
                        f" • {member.get('kills') or 0}/{member.get('deaths') or 0}"
                        f" • {member.get('role') or '-'}"
                    )
                    if str(member.get("player_id") or "") == str(player_id or ""):
                        entry = f"**{entry}**"
                    member_lines.append(entry)
                fields.append(
                    {
                        "name": f"👥 Squad Members ({len(member_lines)})",
                        "value": _truncate("\n".join(member_lines), 1024),
                        "inline": False,
                    }
                )
        else:
            fields.extend(
                [
                {
                    "name": "⚔️ Combat",
                    "value": _field_block(
                        _metric("Kills", kills),
                        _metric("Deaths", deaths),
                        _metric("K/D", kd),
                    ),
                    "inline": True,
                },
                {
                    "name": "⚡ Performance",
                    "value": _field_block(
                        _metric("KPM", f"{kpm:.2f}" if kpm is not None else None),
                        _metric("Streak", stat_snapshot.get("kills_streak")),
                        _metric(
                            "Time",
                            (
                                f"{playtime_hours:.1f} h"
                                if playtime_hours is not None
                                else None
                            ),
                        ),
                    ),
                    "inline": True,
                },
                {
                    "name": "⚠️ Teamkills",
                    "value": _field_block(
                        _metric("Count", stat_snapshot.get("teamkills")),
                        _metric("Streak", stat_snapshot.get("teamkills_streak")),
                    ),
                    "inline": True,
                },
                ]
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
                        "🤖 KI-Einschätzung" if language == "de" else "🤖 AI assessment"
                    ),
                    "value": _truncate(
                        f"**Risiko:** {analysis.risk_score:.0%}\n"
                        f"**Kategorie:** {categories}\n{analysis.rationale}",
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
    if action_log:
        fields.append(action_log)
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
    has_action_target = bool(player_id)
    if status in {"resolved", "dismissed"}:
        pass
    elif not moderation_ready:
        fields.append(
            {"name": "Discord", "value": labels["not_configured"], "inline": False}
        )
    else:
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
                ("message", 2, f"📧 {_truncate(target_name, 65)}"),
                ("punish", 1, "💀 Bestrafen" if language == "de" else "💀 Punish"),
                ("kick", 3, "🤜 Kicken" if language == "de" else "🤜 Kick"),
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
                if has_action_target and action in allowed_actions
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
            for action, style, label in [
                ("remove_from_squad", 1, "🥾 Squad Kick"),
                (
                    "disband_squad",
                    4,
                    "💣 Squad auflösen" if language == "de" else "💣 Disband squad",
                ),
            ]:
                if has_action_target and action in allowed_actions:
                    context_row.append(
                        {
                            "type": 2,
                            "style": style,
                            "label": label,
                            "custom_id": f"action:{incident_id}:{revision}:{action}",
                        }
                    )
            if has_action_target:
                context_row.append(
                    {
                        "type": 2,
                        "style": 2,
                        "label": "📄 Logs",
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
    footer_parts = []
    if assigned_name:
        footer_parts.append(
            ("Bearbeitet von " if language == "de" else "Handled by ") + assigned_name
        )
    footer_parts.extend(
        [
            "HLL Unit Report" if is_squad_report else "HLL Player Report",
            f"{envelope.server_name} · #{envelope.server_number} · {game_label}",
        ]
    )
    return {
        "embeds": [
            {
                "title": _truncate(f"{team_emoji} {title}", 256),
                "description": _truncate(identity, 4096),
                "color": color,
                "fields": fields[:25],
                "footer": {"text": _truncate(" | ".join(footer_parts), 2048)},
            }
        ],
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
