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
            "name_alert": "KI-Namensprüfung",
            "chat_alert": "KI-Chatprüfung",
            "server": "Server",
            "source": "Quelle",
            "reporter": "Reporter",
            "affected": "Betroffen",
            "reason": "📣 Grund der Meldung",
            "combat": "⚔️ Kampf",
            "performance": "⚡ Leistung",
            "unit": "👥 Einheit",
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
            "name_alert": "AI name review",
            "chat_alert": "AI chat review",
            "server": "Server",
            "source": "Source",
            "reporter": "Reporter",
            "affected": "Affected",
            "reason": "📣 Report reason",
            "combat": "⚔️ Combat",
            "performance": "⚡ Performance",
            "unit": "👥 Unit",
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
    source = str(incident.get("source") or "manual")
    title_kind = labels[
        (
            "name_alert"
            if source == "ai_player_name"
            else "chat_alert" if source == "ai_chat" else "incident"
        )
    ]
    team_emoji, color = _team_style(team, analysis.risk_score if analysis else None)
    identity = f"👤 **{_truncate(target_name, 200)}**"
    if player_id:
        identity += f"\n🆔 `{_truncate(player_id, 100)}`"
    identity += (
        f"\n🎮 **{envelope.server_name} · #{envelope.server_number} · {game_label}**"
        f"\n📡 {source_labels.get(source, source)}"
    )
    reporter_name = incident.get("reporter_name")
    if reporter_name:
        identity += f"\n👮 {labels['reporter']}: **{_truncate(reporter_name, 180)}**"
    fields = [
        {
            "name": labels["reason"],
            "value": _truncate(incident.get("reason"), 1024),
            "inline": False,
        },
        {
            "name": labels["combat"],
            "value": _field_block(
                _metric("Kills", kills),
                _metric("Deaths", deaths),
                _metric("K/D", kd),
                _metric("Teamkills", snapshot.get("teamkills")),
            ),
            "inline": True,
        },
        {
            "name": labels["performance"],
            "value": _field_block(
                _metric("Level", snapshot.get("level")),
                _metric("Combat", snapshot.get("combat")),
                _metric("Spielzeit" if language == "de" else "Playtime", playtime),
            ),
            "inline": True,
        },
        {
            "name": labels["unit"],
            "value": _field_block(
                _metric("Team", team),
                _metric(
                    "Squad",
                    primary.get("squad_name")
                    or snapshot.get("unit_name")
                    or snapshot.get("squad_name"),
                ),
                _metric(
                    "Rolle" if language == "de" else "Role",
                    primary.get("role") or snapshot.get("role"),
                ),
            ),
            "inline": True,
        },
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
        },
    ]
    if analysis:
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
    elif ai_unavailable:
        fields.append(
            {"name": "KI / AI", "value": labels["unavailable"], "inline": False}
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
    if not moderation_ready:
        fields.append(
            {"name": "Discord", "value": labels["not_configured"], "inline": False}
        )
    elif status not in {"resolved", "dismissed"}:
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
        recommended = analysis.suggested_action.value if analysis else None
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
