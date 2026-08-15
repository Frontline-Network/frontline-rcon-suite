from __future__ import annotations

import hashlib

import httpx

from .config import Settings, get_settings
from .contracts import IncidentEventEnvelope, ModerationAnalysis


def _truncate(value: object, length: int) -> str:
    text = str(value or "-")
    return text if len(text) <= length else f"{text[: length - 1]}…"


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
            "incident": "Admin-Incident",
            "server": "Server",
            "source": "Quelle",
            "reporter": "Reporter",
            "affected": "Betroffen",
            "context": "Spiel-/Squad-Kontext",
            "status": "Status / Bearbeiter",
            "risk": "KI-Risiko",
            "categories": "Kategorie / Regeln",
            "recommendation": "Empfehlung",
            "rationale": "Begründung",
            "excerpts": "Relevante Textstellen",
            "player_response": "Spielerantwort (Entwurf, nicht gesendet)",
            "unavailable": "Nicht verfügbar",
            "claim": "Übernehmen",
            "resolve": "Abschließen",
            "dismiss": "Ablehnen",
            "accept": "Empfehlung übernehmen",
        },
        "en": {
            "incident": "Admin incident",
            "server": "Server",
            "source": "Source",
            "reporter": "Reporter",
            "affected": "Affected",
            "context": "Game / squad context",
            "status": "Status / assignee",
            "risk": "AI risk",
            "categories": "Category / rules",
            "recommendation": "Recommendation",
            "rationale": "Rationale",
            "excerpts": "Relevant excerpts",
            "player_response": "Player response (draft, not sent)",
            "unavailable": "Unavailable",
            "claim": "Claim",
            "resolve": "Resolve",
            "dismiss": "Dismiss",
            "accept": "Accept recommendation",
        },
    }.get(language, {})
    snapshot = primary.get("snapshot") or {}
    context_values = {
        "team": primary.get("team") or snapshot.get("team"),
        "squad": primary.get("squad_name") or snapshot.get("squad_name"),
        "role": primary.get("role") or snapshot.get("role"),
        "level": snapshot.get("level"),
        "kills": snapshot.get("kills"),
        "deaths": snapshot.get("deaths"),
        "score": snapshot.get("score") or snapshot.get("combat"),
    }
    context = (
        " · ".join(
            f"{key}: {value}"
            for key, value in context_values.items()
            if value is not None
        )
        or "-"
    )
    fields = [
        {
            "name": labels["server"],
            "value": _truncate(
                f"{envelope.server_name} · #{envelope.server_number} · {envelope.game}",
                1024,
            ),
            "inline": False,
        },
        {
            "name": labels["source"],
            "value": _truncate(incident.get("source"), 1024),
            "inline": True,
        },
        {
            "name": labels["reporter"],
            "value": _truncate(incident.get("reporter_name"), 1024),
            "inline": True,
        },
        {
            "name": labels["affected"],
            "value": _truncate(
                primary.get("display_name") or incident.get("target_name"), 1024
            ),
            "inline": True,
        },
        {
            "name": labels["context"],
            "value": _truncate(context, 1024),
            "inline": False,
        },
        {
            "name": labels["status"],
            "value": _truncate(
                f"{incident.get('status', 'new')} · {incident.get('assigned_to') or '-'}",
                1024,
            ),
            "inline": False,
        },
    ]
    if analysis:
        fields.extend(
            [
                {
                    "name": labels["risk"],
                    "value": f"{analysis.severity.value} · {analysis.risk_score:.0%}",
                    "inline": True,
                },
                {
                    "name": labels["categories"],
                    "value": _truncate(
                        " · ".join(
                            [
                                ", ".join(analysis.categories) or "-",
                                ", ".join(analysis.rule_ids) or "-",
                            ]
                        ),
                        1024,
                    ),
                    "inline": True,
                },
                {
                    "name": labels["recommendation"],
                    "value": _truncate(
                        " · ".join(
                            value
                            for value in [
                                analysis.suggested_action.value,
                                (
                                    f"{analysis.suggested_duration_hours}h"
                                    if analysis.suggested_duration_hours
                                    else None
                                ),
                            ]
                            if value
                        ),
                        1024,
                    ),
                    "inline": True,
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
    components = [
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
    ]
    if (
        analysis
        and analysis.suggested_action.value not in {"none", "manual_review"}
        and analysis.suggested_action.value in allowed_actions
    ):
        components.append(
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": (
                            4
                            if analysis.suggested_action.value
                            in {"perma_ban", "blacklist", "disband_squad"}
                            else 1
                        ),
                        "label": labels["accept"],
                        "custom_id": f"recommend:{incident_id}:{revision}:{analysis.suggested_action.value}",
                    }
                ],
            }
        )
    if allowed_actions:
        components.append(
            {
                "type": 1,
                "components": [
                    {
                        "type": 3,
                        "custom_id": f"choose:{incident_id}:{revision}",
                        "placeholder": (
                            "Manuelle Aktion wählen"
                            if language == "de"
                            else "Choose a manual action"
                        ),
                        "min_values": 1,
                        "max_values": 1,
                        "options": [
                            {"label": action.replace("_", " ")[:100], "value": action}
                            for action in allowed_actions
                        ],
                    }
                ],
            }
        )
    return {
        "embeds": [
            {
                "title": _truncate(
                    f"{labels['incident']} · {envelope.server_name}", 256
                ),
                "description": _truncate(incident.get("reason"), 4096),
                "color": (
                    15158332 if analysis and analysis.risk_score >= 0.9 else 3447003
                ),
                "fields": fields[:25],
                "footer": {
                    "text": _truncate(
                        " · ".join(
                            value
                            for value in [
                                f"Incident {incident_id}",
                                f"Revision {revision}",
                                (
                                    f"{analysis.model_version} / {analysis.prompt_version} / "
                                    f"{analysis.policy_profile_id}:{analysis.policy_version}"
                                    if analysis
                                    else None
                                ),
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
