from __future__ import annotations

import hashlib

import httpx

from .config import Settings, get_settings
from .contracts import IncidentEventEnvelope, ModerationAnalysis


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
            "incident": "Admin-Meldung",
            "name_alert": "Spielername prüfen",
            "chat_alert": "Chatnachricht prüfen",
            "server": "Server",
            "source": "Quelle",
            "reporter": "Reporter",
            "affected": "Betroffen",
            "reason": "📣 Grund der Meldung",
            "combat": "⚔️ Kampf",
            "performance": "⚡ Leistung",
            "unit": "👥 Einheit",
            "teamkills": "⚠️ Teamkills",
            "status": "📌 Bearbeitung",
            "ai_assessment": "🤖 KI-Einschätzung",
            "rationale": "🧾 KI-Begründung",
            "excerpts": "Relevante Textstellen",
            "player_response": "💬 Antwortvorschlag (nicht gesendet)",
            "unavailable": "Nicht verfügbar",
            "claim": "🙋 Übernehmen",
            "resolve": "✅ Abschließen",
            "dismiss": "🚫 Ablehnen",
            "not_configured": "⚙️ Keine Moderatorrolle eingerichtet. Aktionen sind gesperrt.",
        },
        "en": {
            "incident": "Admin report",
            "name_alert": "Review player name",
            "chat_alert": "Review chat message",
            "server": "Server",
            "source": "Source",
            "reporter": "Reporter",
            "affected": "Affected",
            "reason": "📣 Report reason",
            "combat": "⚔️ Combat",
            "performance": "⚡ Performance",
            "unit": "👥 Unit",
            "teamkills": "⚠️ Teamkills",
            "status": "📌 Processing",
            "ai_assessment": "🤖 AI assessment",
            "rationale": "🧾 AI rationale",
            "excerpts": "Relevant excerpts",
            "player_response": "💬 Suggested reply (not sent)",
            "unavailable": "Unavailable",
            "claim": "🙋 Claim",
            "resolve": "✅ Complete",
            "dismiss": "🚫 Reject",
            "not_configured": "⚙️ No moderator role configured. Actions are locked.",
        },
    }.get(language, {})
    snapshot = primary.get("snapshot") or {}
    team = primary.get("team") or snapshot.get("team")
    target_name = primary.get("display_name") or incident.get("target_name") or "-"
    player_id = (
        primary.get("player_id")
        or snapshot.get("player_id")
        or incident.get("target_id")
    )
    kills = snapshot.get("kills")
    deaths = snapshot.get("deaths")
    kd = None
    if isinstance(kills, (int, float)) and isinstance(deaths, (int, float)):
        kd = f"{kills / max(deaths, 1):.2f}"
    playtime = snapshot.get("map_playtime_seconds")
    if isinstance(playtime, (int, float)):
        playtime = f"{playtime / 60:.0f} min"
    game_label = "HLL Vietnam" if envelope.game == "hll_vietnam" else "Hell Let Loose"
    source_labels = {
        "chat": "!admin",
        "manual": "Manuell" if language == "de" else "Manual",
        "ai_chat": "KI-Chat" if language == "de" else "AI chat",
        "ai_player_name": "KI-Spielername" if language == "de" else "AI player name",
    }
    status_labels = {
        "new": "Neu" if language == "de" else "New",
        "claimed": "Übernommen" if language == "de" else "Claimed",
        "resolved": "Abgeschlossen" if language == "de" else "Completed",
        "dismissed": "Abgelehnt" if language == "de" else "Rejected",
    }
    action_labels = {
        "none": "Keine Aktion" if language == "de" else "No action",
        "manual_review": "Manuell prüfen" if language == "de" else "Manual review",
        "message": "Nachricht" if language == "de" else "Message",
        "punish": "Punish",
        "kick": "Kick",
        "temp_ban": "Tempban",
        "perma_ban": "Permaban",
        "blacklist": "Blacklist",
        "remove_from_squad": "Squad-Kick",
        "disband_squad": "Squad auflösen" if language == "de" else "Disband squad",
    }
    severity_labels = {
        "none": "kein Risiko" if language == "de" else "no risk",
        "low": "niedrig" if language == "de" else "low",
        "medium": "mittel" if language == "de" else "medium",
        "high": "hoch" if language == "de" else "high",
        "critical": "kritisch" if language == "de" else "critical",
    }
    category_labels = {
        "violence": "Gewalt" if language == "de" else "Violence",
        "harassment": "Belästigung" if language == "de" else "Harassment",
        "hate": "Hassrede" if language == "de" else "Hate",
        "sexual": "Sexuell" if language == "de" else "Sexual",
        "self-harm": "Selbstverletzung" if language == "de" else "Self-harm",
    }
    source = str(incident.get("source") or "manual")
    title_kind = labels[
        (
            "name_alert"
            if source == "ai_player_name"
            else "chat_alert" if source == "ai_chat" else "incident"
        )
    ]
    team_emoji, color = _team_style(team, analysis.risk_score if analysis else None)
    if source == "ai_player_name":
        team_emoji = "🔎"
    identity = f"👤 **{_truncate(target_name, 200)}**"
    if player_id:
        identity += f"\n🆔 `{_truncate(player_id, 100)}`"
    identity += (
        f"\n🎮 **{envelope.server_name} · #{envelope.server_number} · {game_label}**"
    )
    if source != "ai_player_name":
        identity += f"\n📡 {source_labels.get(source, source)}"
    if source in {"chat", "manual"}:
        unit_context = " · ".join(
            str(value)
            for value in [
                team,
                primary.get("squad_name")
                or snapshot.get("unit_name")
                or snapshot.get("squad_name"),
                primary.get("role") or snapshot.get("role"),
            ]
            if _present(value)
        )
        if unit_context:
            identity += f"\n👥 {unit_context}"
    reporter_name = incident.get("reporter_name")
    if reporter_name:
        identity += f"\n👮 {labels['reporter']}: **{_truncate(reporter_name, 180)}**"
    fields = []
    if source != "ai_player_name":
        fields.append(
            {
                "name": labels["reason"],
                "value": _truncate(incident.get("reason"), 1024),
                "inline": False,
            }
        )
        stat_groups = [
            (
                labels["combat"],
                [
                    _metric("Kills", kills),
                    _metric("Deaths", deaths),
                    _metric("K/D", kd),
                ],
            ),
            (
                labels["performance"],
                [
                    _metric("Level", snapshot.get("level")),
                    _metric("Combat", snapshot.get("combat")),
                    _metric("Spielzeit" if language == "de" else "Playtime", playtime),
                ],
            ),
            (
                labels["teamkills"],
                [
                    _metric(
                        "Anzahl" if language == "de" else "Count",
                        snapshot.get("teamkills"),
                    ),
                ],
            ),
        ]
        fields.extend(
            {
                "name": name,
                "value": _field_block(*values),
                "inline": True,
            }
            for name, values in stat_groups
            if any(values)
        )
    if analysis and source == "ai_player_name":
        categories = ", ".join(
            category_labels.get(value, value.replace("_", " ").title())
            for value in analysis.categories
        )
        assessment_lines = [
            (
                f"**{analysis.risk_score:.0%} · "
                f"{severity_labels.get(analysis.severity.value, analysis.severity.value)}**"
            ),
            f"**Kategorie:** {categories}" if categories else None,
            analysis.rationale,
        ]
        recommendation_lines = [
            f"**{action_labels.get(analysis.suggested_action.value, analysis.suggested_action.value)}**",
            analysis.suggested_player_response,
        ]
        fields.extend(
            [
                {
                    "name": "🧠 Einschätzung" if language == "de" else "🧠 Assessment",
                    "value": _truncate(_field_block(*assessment_lines), 1024),
                    "inline": False,
                },
                {
                    "name": (
                        "💡 Empfehlung" if language == "de" else "💡 Recommendation"
                    ),
                    "value": _truncate(_field_block(*recommendation_lines), 1024),
                    "inline": False,
                },
            ]
        )
    elif analysis and source == "ai_chat":
        fields.extend(
            [
                {
                    "name": labels["ai_assessment"],
                    "value": _truncate(
                        "\n".join(
                            [
                                f"**Risiko:** {severity_labels.get(analysis.severity.value, analysis.severity.value)} · {analysis.risk_score:.0%}",
                                f"**Kategorie:** {', '.join(analysis.categories) or '-'}",
                                f"**Regeln:** {', '.join(analysis.rule_ids) or '-'}",
                                f"**Empfehlung:** {action_labels.get(analysis.suggested_action.value, analysis.suggested_action.value)}"
                                + (
                                    f" · {analysis.suggested_duration_hours} h"
                                    if analysis.suggested_duration_hours
                                    else ""
                                ),
                            ]
                        ),
                        1024,
                    ),
                    "inline": False,
                },
                {
                    "name": labels["rationale"],
                    "value": _truncate(analysis.rationale, 1024),
                    "inline": False,
                },
            ]
        )
        if analysis.relevant_excerpts:
            fields.append(
                {
                    "name": labels["excerpts"],
                    "value": _truncate(
                        "\n".join(f"• {value}" for value in analysis.relevant_excerpts),
                        1024,
                    ),
                    "inline": False,
                }
            )
        if analysis.suggested_player_response:
            fields.append(
                {
                    "name": labels["player_response"],
                    "value": _truncate(analysis.suggested_player_response, 1024),
                    "inline": False,
                }
            )
    elif ai_unavailable and source in {"ai_chat", "ai_player_name"}:
        fields.append(
            {"name": "KI / AI", "value": labels["unavailable"], "inline": False}
        )
    fields.append(
        {
            "name": labels["status"],
            "value": _truncate(
                " · ".join(
                    value
                    for value in [
                        status_labels.get(
                            str(incident.get("status", "new")),
                            str(incident.get("status", "new")),
                        ),
                        incident.get("assigned_to"),
                    ]
                    if value
                ),
                1024,
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
    status = str(incident.get("status") or "new")
    if status in {"resolved", "dismissed"}:
        pass
    elif not moderation_ready:
        fields.append(
            {"name": "Discord", "value": labels["not_configured"], "inline": False}
        )
    else:
        action_icons = {
            "message": "💬",
            "punish": "⚠️",
            "kick": "👢",
            "temp_ban": "⏱️",
            "perma_ban": "🔨",
            "blacklist": "⛔",
            "remove_from_squad": "↪️",
            "disband_squad": "💥",
        }
        recommended = (
            analysis.suggested_action.value
            if analysis and source in {"ai_chat", "ai_player_name"}
            else None
        )
        action_buttons = [
            {
                "type": 2,
                "style": (
                    4
                    if action in {"perma_ban", "blacklist", "disband_squad"}
                    else 1 if action == recommended else 2
                ),
                "label": _truncate(
                    f"{'✨' if action == recommended else action_icons[action]} {action_labels[action]}",
                    80,
                ),
                "custom_id": f"recommend:{incident_id}:{revision}:{action}",
            }
            for action in allowed_actions
        ]
        for offset in range(0, len(action_buttons), 5):
            components.append(
                {"type": 1, "components": action_buttons[offset : offset + 5]}
            )
        components.append(
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 1,
                        "label": labels["claim"],
                        "custom_id": f"claim:{incident_id}:{revision}",
                    },
                    {
                        "type": 2,
                        "style": 3,
                        "label": labels["resolve"],
                        "custom_id": f"resolve:{incident_id}:{revision}",
                    },
                    {
                        "type": 2,
                        "style": 2,
                        "label": labels["dismiss"],
                        "custom_id": f"dismiss:{incident_id}:{revision}",
                    },
                ],
            }
        )
    return {
        "embeds": [
            {
                "title": _truncate(f"{team_emoji} {title_kind}: {target_name}", 256),
                "description": _truncate(identity, 4096),
                "color": color,
                "fields": fields[:25],
                "footer": {
                    "text": _truncate(
                        " · ".join(
                            value
                            for value in [
                                f"CRCON #{envelope.server_number}",
                                f"Incident {incident_id[:8]}",
                                f"Revision {revision}",
                            ]
                            if value
                        ),
                        2048,
                    )
                },
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
