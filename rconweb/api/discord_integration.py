"""CRCON-side Discord Report Bot configuration and interaction boundary."""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import timedelta

import requests
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rcon.admin_incidents import (
    IncidentConflict,
    IncidentNotFound,
    complete_incident_action,
    confirmed_action_subject,
    get_incident,
    mutate_incident,
    reserve_incident_action,
)
from rcon.message_templates import get_message_templates
from rcon.moderation import (
    DiscordActor,
    DiscordInteractionRequest,
    ModerationAnalysis,
    ModerationFeedback,
    ModerationPolicy,
    SuggestedAction,
)
from rcon.moderation_candidates import persist_candidate_analysis
from rcon.moderation_store import persist_analysis
from rcon.types import MessageTemplateCategory

from .auth import api_response, login_required
from .decorators import require_http_methods
from .discord_capabilities import (
    capability_digest,
    capability_matches,
    decrypt_capability,
    encrypt_capability,
    new_capability,
)
from .mobile import _error, _json_body
from .mobile_incidents import _execute_action
from .models import (
    DiscordInteractionReceipt,
    DiscordModerationFeedback,
    DiscordPairing,
    DiscordPreparedAction,
    DiscordReportIntegration,
)

ALL_ACTIONS = {item.value for item in SuggestedAction} - {
    SuggestedAction.NONE.value,
    SuggestedAction.MANUAL_REVIEW.value,
}
DESTRUCTIVE_ACTIONS = {"perma_ban", "blacklist", "disband_squad"}
DEFAULT_REPORTER_TEMPLATES = {
    "received": "Dein Admin-Report ist eingegangen.",
    "claimed": "Dein Admin-Report wird jetzt bearbeitet.",
    "resolved": "Dein Admin-Report wurde abgeschlossen.",
    "dismissed": "Dein Admin-Report wurde abgelehnt.",
}
DEFAULT_AI_CONFIG = {
    "reports_enabled": False,
    "chat_enabled": False,
    "names_enabled": False,
    "shadow_mode": True,
    "quality_opt_in": False,
    "provider": "managed",
    "ai_model": "gpt-5.6-luna",
    "player_name_model": "gpt-5.4-nano",
}
AI_PROVIDERS = {"managed", "api_key", "codex"}
API_MODEL_OPTIONS = (
    {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano"},
    {"id": "gpt-5.6-luna", "name": "GPT-5.6 Luna"},
    {"id": "gpt-5.6-terra", "name": "GPT-5.6 Terra"},
    {"id": "gpt-5.6-sol", "name": "GPT-5.6 Sol"},
)
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
SQUAD_LEADER_ROLES = {
    "officer",
    "squadleader",
    "tankcommander",
    "spotter",
    "artilleryobserver",
    "mortarobserver",
    "helicopterlogisticsofficer",
}


def _json_safe(value):
    """Normalize audited results before storing them in Django JSONFields."""

    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def _integration() -> DiscordReportIntegration:
    service_url = os.getenv("DISCORD_SERVICE_URL", "").rstrip("/")
    integration, _ = DiscordReportIntegration.objects.get_or_create(
        pk=1, defaults={"service_url": service_url}
    )
    if service_url and not integration.service_url:
        integration.service_url = service_url
        integration.save(update_fields=["service_url", "updated_at"])
    return integration


def _new_pairing(request) -> tuple[DiscordPairing, str, dict]:
    DiscordPairing.objects.filter(state=DiscordPairing.State.PENDING).delete()
    secret = new_capability("pair")
    pairing = DiscordPairing.objects.create(
        secret_digest=capability_digest(secret),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    payload = {
        "crcon_callback_url": request.build_absolute_uri(
            "/api/discord/v1/pairings/complete"
        ),
        "pairing_id": str(pairing.id),
        "pairing_secret": secret,
    }
    return pairing, secret, payload


def _service_error(response, fallback: str) -> str:
    """Expose the central service's safe API detail, not a generic HTTP error."""

    try:
        detail = response.json().get("detail")
    except (AttributeError, TypeError, ValueError):
        detail = None
    return str(detail)[:500] if detail else fallback


def _serialized(integration: DiscordReportIntegration) -> dict:
    return {
        "installation_id": str(integration.installation_id),
        "enabled": integration.enabled,
        "connected": bool(
            integration.guild_id
            and integration.channel_id
            and integration.inbound_capability_digest
            and integration.outbound_capability_ciphertext
        ),
        "service_url": integration.service_url,
        "guild_id": integration.guild_id,
        "guild_name": integration.guild_name,
        "channel_id": integration.channel_id,
        "channel_name": integration.channel_name,
        "moderator_role_ids": integration.moderator_role_ids,
        "allowed_actions": integration.allowed_actions,
        "language": integration.language,
        "ai_config": {**DEFAULT_AI_CONFIG, **(integration.ai_config or {})},
        "has_api_key": bool(integration.ai_api_key_ciphertext),
        "api_model_options": list(API_MODEL_OPTIONS),
        "policy": integration.policy,
        "reporter_templates": {
            **DEFAULT_REPORTER_TEMPLATES,
            **(integration.reporter_templates or {}),
        },
    }


def _require_manager(request, command: str) -> HttpResponse | None:
    if not request.user.has_perm("api.can_manage_discord_report_bot"):
        return _error(command, "Missing Discord integration permission", 403)
    return None


def _bearer(request) -> str:
    value = request.headers.get("Authorization", "")
    return value[7:] if value.startswith("Bearer ") else ""


def _authorized_integration(request, command: str):
    integration = _integration()
    if not integration.enabled or not capability_matches(
        _bearer(request), integration.inbound_capability_digest
    ):
        return None, _error(command, "Unknown Discord capability", 404)
    return integration, None


def _validate_binding(
    integration: DiscordReportIntegration,
    *,
    guild_id: str,
    channel_id: str,
    actor: DiscordActor,
    action: str | None = None,
) -> None:
    if guild_id != integration.guild_id or channel_id != integration.channel_id:
        raise PermissionError("Discord guild or channel does not match integration")
    if not set(actor.role_ids).intersection(integration.moderator_role_ids or []):
        raise PermissionError("No currently allowed Discord moderator role")
    if action and action not in set(integration.allowed_actions or []):
        raise PermissionError("Discord action is disabled in CRCON")


def _normalize_action_subject(incident: dict, arguments: dict) -> dict:
    """Derive confirmation state from CRCON data, never from Discord input."""

    normalized = dict(arguments)
    if normalized.get("reporter_action") is True:
        reporter_id = str(incident.get("reporter_id") or "").strip()
        if not reporter_id:
            raise ValueError("This incident has no in-game reporter")
        normalized["player_id"] = reporter_id
        normalized.pop("subject_id", None)
        normalized.pop("confirm_subject_id", None)
        return normalized
    subject_id = str(normalized.get("subject_id") or "").strip()
    subject = next(
        (
            item
            for item in incident.get("subjects") or []
            if str(item.get("id") or "") == subject_id
        ),
        None,
    )
    if subject_id and not subject:
        raise ValueError("The selected incident subject does not exist")
    if subject:
        # Discord only selects an opaque subject ID. Always derive the actual
        # player target from current CRCON data so a stale or forged player ID
        # can never redirect the action to another player.
        normalized.pop("player_id", None)
        normalized.pop("player_name", None)
    if (
        subject
        and subject.get("kind") == "player"
        and subject.get("state") == "suggested"
    ):
        normalized["confirm_subject_id"] = subject_id
    else:
        normalized.pop("confirm_subject_id", None)
    if (
        not normalized.get("player_id")
        and subject
        and subject.get("kind") == "player"
        and subject.get("player_id")
    ):
        normalized["player_id"] = str(subject["player_id"])
        normalized["player_name"] = str(
            subject.get("display_name") or subject.get("player_name") or ""
        )
    if not normalized.get("player_id") and subject and subject.get("kind") == "squad":
        snapshot = subject.get("snapshot") or {}
        leader = snapshot.get("leader") or {}
        candidates = [leader, *(snapshot.get("players") or [])]
        for candidate in candidates:
            role = re.sub(
                r"[^a-z0-9]",
                "",
                str(candidate.get("role") or "").casefold(),
            )
            if candidate and (candidate is leader or role in SQUAD_LEADER_ROLES):
                player_id = str(candidate.get("player_id") or "").strip()
                if player_id:
                    normalized["player_id"] = player_id
                    normalized.setdefault("player_name", candidate.get("name"))
                    break
    if not subject and not normalized.get("player_id") and incident.get("target_id"):
        normalized["player_id"] = str(incident["target_id"])
        normalized.setdefault("player_name", incident.get("target_name"))
    return normalized


def _selected_subject_name(incident: dict, arguments: dict) -> str:
    subject_id = str(arguments.get("subject_id") or "").strip()
    subject = next(
        (
            item
            for item in incident.get("subjects") or []
            if str(item.get("id") or "") == subject_id
        ),
        {},
    )
    return str(
        arguments.get("player_name")
        or subject.get("leader_name")
        or subject.get("display_name")
        or subject.get("squad_name")
        or incident.get("target_name")
        or "selected subject"
    )


def _should_auto_resolve_after_action(incident: dict) -> bool:
    confirmed = [
        subject
        for subject in incident.get("subjects") or []
        if subject.get("state") == "confirmed"
        and subject.get("kind") in {"player", "squad"}
    ]
    return len(confirmed) <= 1


def _validate_prepared_action_target(action: str, incident: dict, arguments: dict):
    """Reject targetless game actions before claiming the incident."""

    if action == "disband_squad":
        subject_id = str(arguments.get("subject_id") or "").strip()
        subject = next(
            (
                item
                for item in incident.get("subjects") or []
                if str(item.get("id") or "") == subject_id
            ),
            None,
        )
        has_squad_context = bool(
            subject
            and subject.get("state") == "confirmed"
            and subject.get("kind") in {"player", "squad"}
            and subject.get("team")
            and (subject.get("squad_name") or subject.get("display_name"))
        )
        if not has_squad_context:
            raise ValueError("Select a confirmed squad before running this action")
        return
    confirm_subject_id = str(arguments.get("confirm_subject_id") or "").strip()
    if confirm_subject_id:
        subject = next(
            (
                item
                for item in incident.get("subjects") or []
                if str(item.get("id") or "") == confirm_subject_id
            ),
            None,
        )
        if (
            not subject
            or subject.get("kind") != "player"
            or subject.get("state") != "suggested"
            or str(subject.get("player_id") or "")
            != str(arguments.get("player_id") or "")
        ):
            raise ValueError("Select an affected player before running this action")
        return
    confirmed_action_subject(
        incident,
        player_id=str(arguments.get("player_id") or ""),
        subject_id=str(arguments.get("subject_id") or "").strip() or None,
        allow_reporter=arguments.get("reporter_action") is True,
    )


@csrf_exempt
@require_http_methods(["POST"])
def discord_action_templates(request):
    """Return CRCON's shared action templates without persisting them centrally."""

    command = "discord_action_templates"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        actor = DiscordActor.model_validate(data["actor"])
        action = str(data["action"])
        _validate_binding(
            integration,
            guild_id=str(data["guild_id"]),
            channel_id=str(data["channel_id"]),
            actor=actor,
            action=action,
        )
        category = (
            MessageTemplateCategory.MESSAGE
            if action == SuggestedAction.MESSAGE.value
            else MessageTemplateCategory.REASON
        )
        templates = get_message_templates(category)
        selected_id = data.get("template_id")
        selected = None
        if selected_id is not None:
            selected_id = int(selected_id)
            match = next(
                (item for item in templates if int(item["id"]) == selected_id), None
            )
            if match is None:
                raise ValueError("Template does not exist in this action category")
            selected = {
                "id": int(match["id"]),
                "title": str(match["title"])[:100],
                "content": str(match["content"])[:1000],
            }
        result = {
            "category": category.value,
            "templates": [
                {"id": int(item["id"]), "title": str(item["title"])[:100]}
                for item in templates[:24]
            ],
            "selected": selected,
        }
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@require_http_methods(["POST"])
def incident_logs(request):
    """Return a short, read-only 24 hour excerpt for the claimed report player."""

    command = "discord_incident_logs"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        actor = DiscordActor.model_validate(data["actor"])
        _validate_binding(
            integration,
            guild_id=str(data["guild_id"]),
            channel_id=str(data["channel_id"]),
            actor=actor,
        )
        incident = get_incident(str(data["incident_id"]))
        actor_name = f"discord:{actor.discord_id}:{actor.display_name}"[:150]
        if incident.get("assigned_to") != actor_name:
            raise IncidentConflict("Incident is already claimed by another admin")
        requested_subject_id = str(data.get("subject_id") or "").strip()
        subject = next(
            (
                item
                for item in incident.get("subjects") or []
                if str(item.get("id") or "") == requested_subject_id
            ),
            incident.get("primary_subject") or {},
        )
        normalized = _normalize_action_subject(
            incident, {"subject_id": str(subject.get("id") or "")}
        )
        player_id = str(normalized.get("player_id") or "")
        if not player_id:
            raise ValueError("Select a confirmed player before requesting logs")
        player_name = str(
            normalized.get("player_name")
            or subject.get("display_name")
            or incident.get("target_name")
            or "Spieler"
        )
        from rcon.api_commands import get_rcon_api

        records = get_rcon_api().get_historical_logs(
            player_id=player_id,
            from_=timezone.now() - timedelta(hours=24),
            till=timezone.now(),
            limit=25,
            time_sort="desc",
            exact_player_match=True,
            server_filter=str(incident["server_number"]),
        )
        lines = []
        for record in records or []:
            occurred = record.get("event_time") or record.get("creation_time") or ""
            occurred_text = str(occurred)
            if "T" in occurred_text:
                occurred_text = occurred_text.split("T", 1)[1][:8]
            action = str(record.get("type") or "LOG")
            first = str(record.get("player1_name") or "")
            second = str(record.get("player2_name") or "")
            content = str(record.get("content") or "")
            details = " → ".join(value for value in [first, second] if value)
            if content:
                details = f"{details}: {content}" if details else content
            lines.append(f"{occurred_text} [{action}] {details}".strip()[:240])
        result = {
            "incident_id": str(incident["id"]),
            "player_id": player_id,
            "player_name": player_name,
            "lines": lines,
        }
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    return api_response(command=command, failed=False, result=result)


def _config_payload(data: dict) -> dict:
    language = str(data.get("language", "de"))
    if language not in {"de", "en"}:
        raise ValueError("language must be de or en")
    roles = [str(value) for value in data.get("moderator_role_ids", [])]
    if any(not re.fullmatch(r"[0-9]+", value) for value in roles):
        raise ValueError("Discord role IDs must be numeric")
    actions = set(map(str, data.get("allowed_actions", [])))
    if not actions.issubset(ALL_ACTIONS):
        raise ValueError("Unknown Discord action")
    policy = ModerationPolicy.model_validate(data.get("policy") or {}).model_dump(
        mode="json"
    )
    ai_config = {**DEFAULT_AI_CONFIG, **dict(data.get("ai_config") or {})}
    # Normal player/admin reports deliberately use CRCON's deterministic
    # moderator workflow and never require managed AI analysis.
    ai_config["reports_enabled"] = False
    allowed_ai_keys = {
        "reports_enabled",
        "chat_enabled",
        "names_enabled",
        "shadow_mode",
        "quality_opt_in",
        "provider",
        "ai_model",
        "player_name_model",
    }
    if set(ai_config) - allowed_ai_keys:
        raise ValueError("Unknown AI configuration field")
    if ai_config["provider"] not in AI_PROVIDERS:
        raise ValueError("Unknown AI provider")
    for key in ("ai_model", "player_name_model"):
        ai_config[key] = str(ai_config.get(key) or DEFAULT_AI_CONFIG[key])
        if not _MODEL_ID_RE.fullmatch(ai_config[key]):
            raise ValueError("Invalid AI model ID")
    templates = {
        str(key): str(value)[:500]
        for key, value in dict(data.get("reporter_templates") or {}).items()
        if key in DEFAULT_REPORTER_TEMPLATES
    }
    return {
        "enabled": bool(data.get("enabled")),
        "moderator_role_ids": list(dict.fromkeys(roles)),
        "allowed_actions": sorted(actions),
        "language": language,
        "ai_config": ai_config,
        "policy": policy,
        "reporter_templates": templates,
    }


@csrf_exempt
@login_required()
@require_http_methods(["GET", "PUT", "DELETE"])
def integration_detail(request):
    command = "discord_report_integration"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    if request.method == "GET":
        return api_response(
            command=command, failed=False, result=_serialized(integration)
        )
    if request.method == "DELETE":
        integration.enabled = False
        integration.guild_id = ""
        integration.guild_name = ""
        integration.channel_id = ""
        integration.channel_name = ""
        integration.moderator_role_ids = []
        integration.delivery_started_at = None
        integration.inbound_capability_digest = ""
        integration.outbound_capability_ciphertext = b""
        integration.ai_api_key_ciphertext = b""
        integration.save()
        DiscordPairing.objects.filter(state=DiscordPairing.State.PENDING).delete()
        return api_response(
            command=command, failed=False, result=_serialized(integration)
        )
    try:
        data = _json_body(request)
        for field, value in _config_payload(data).items():
            setattr(integration, field, value)
        supplied_key = data.get("api_key")
        if supplied_key is not None:
            supplied_key = str(supplied_key).strip()
            if supplied_key and not supplied_key.startswith("sk-"):
                raise ValueError("OpenAI API key must start with sk-")
            integration.ai_api_key_ciphertext = (
                encrypt_capability(supplied_key) if supplied_key else b""
            )
        if data.get("clear_api_key"):
            integration.ai_api_key_ciphertext = b""
        if (
            integration.ai_config.get("provider") == "api_key"
            and not integration.ai_api_key_ciphertext
        ):
            raise ValueError("An OpenAI API key is required for this provider")
        integration.save()
    except (TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    return api_response(command=command, failed=False, result=_serialized(integration))


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def integration_options(request):
    command = "discord_report_options"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    try:
        if integration.outbound_capability_ciphertext:
            response = requests.get(
                (
                    f"{integration.service_url.rstrip('/')}/v1/options/"
                    f"{integration.installation_id}"
                ),
                headers={
                    "Authorization": (
                        f"Bearer {decrypt_capability(integration.outbound_capability_ciphertext)}"
                    )
                },
                timeout=10,
            )
        else:
            _, _, pairing_payload = _new_pairing(request)
            response = requests.post(
                f"{integration.service_url.rstrip('/')}/v1/pairing-options",
                json=pairing_payload,
                timeout=15,
            )
        if not response.ok:
            return _error(
                command,
                _service_error(response, "Discord server options are unavailable"),
                response.status_code if 400 <= response.status_code < 500 else 503,
            )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"Discord options unavailable: {exc}", 503)
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def create_discord_pairing(request):
    command = "discord_report_pairing"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    if not integration.service_url.startswith("https://") and not (
        os.getenv("DEBUG", "false").lower() == "true"
        and integration.service_url.startswith("http://")
    ):
        return _error(command, "DISCORD_SERVICE_URL must use HTTPS", 400)
    pairing, secret, _ = _new_pairing(request)
    return api_response(
        command=command,
        failed=False,
        result={
            "pairing_id": str(pairing.id),
            "pairing_secret": secret,
            "expires_at": pairing.expires_at,
            "service_url": integration.service_url,
            "crcon_callback_url": request.build_absolute_uri(
                "/api/discord/v1/pairings/complete"
            ),
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def connect_integration(request):
    """Complete pairing server-to-server after the Discord app was installed."""

    command = "discord_report_connect"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    try:
        data = _json_body(request)
        channel_id = str(data["channel_id"])
        if not re.fullmatch(r"[0-9]+", channel_id):
            raise ValueError("Channel ID must be numeric")
        if not integration.service_url.startswith("https://") and not (
            os.getenv("DEBUG", "false").lower() == "true"
            and integration.service_url.startswith("http://")
        ):
            raise ValueError("DISCORD_SERVICE_URL must use HTTPS")
        _, _, pairing_payload = _new_pairing(request)
        response = requests.post(
            f"{integration.service_url.rstrip('/')}/v1/pairings",
            json={
                **pairing_payload,
                "channel_id": channel_id,
                "channel_name": str(data.get("channel_name") or "")[:128],
            },
            timeout=15,
        )
        if not response.ok:
            return _error(
                command,
                _service_error(response, "Discord pairing failed"),
                response.status_code if 400 <= response.status_code < 500 else 503,
            )
        response.raise_for_status()
        integration.refresh_from_db()
        roles = [str(value) for value in data.get("moderator_role_ids", [])]
        if any(not re.fullmatch(r"[0-9]+", value) for value in roles):
            raise ValueError("Discord role IDs must be numeric")
        integration.moderator_role_ids = list(dict.fromkeys(roles))
        integration.save(update_fields=["moderator_role_ids", "updated_at"])
    except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
        return _error(command, f"Discord pairing failed: {exc}", 400)
    return api_response(command=command, failed=False, result=_serialized(integration))


@csrf_exempt
@require_http_methods(["POST"])
def verify_pairing(request):
    """Let the central service authenticate discovery without consuming pairing."""

    command = "discord_report_pairing_verify"
    try:
        data = _json_body(request)
        pairing = DiscordPairing.objects.get(pk=data["pairing_id"])
        if (
            pairing.state != DiscordPairing.State.PENDING
            or pairing.expires_at <= timezone.now()
            or not capability_matches(
                str(data["pairing_secret"]), pairing.secret_digest
            )
        ):
            return _error(command, "Pairing is invalid or expired", 404)
    except (DiscordPairing.DoesNotExist, KeyError, TypeError, ValueError):
        return _error(command, "Pairing is invalid or expired", 404)
    return api_response(command=command, failed=False, result={"valid": True})


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def complete_pairing(request):
    command = "discord_report_pairing_complete"
    try:
        data = _json_body(request)
        pairing = DiscordPairing.objects.get(pk=data["pairing_id"])
        if not capability_matches(str(data["pairing_secret"]), pairing.secret_digest):
            return _error(command, "Pairing is invalid or expired", 404)
        actor_capability = str(data["crcon_action_capability"])
        if not 32 <= len(actor_capability) <= 255:
            raise ValueError("CRCON action capability has an invalid length")
        event_capability = new_capability("events")
        guild_id = str(data["guild_id"])
        channel_id = str(data["channel_id"])
        if not re.fullmatch(r"[0-9]+", guild_id) or not re.fullmatch(
            r"[0-9]+", channel_id
        ):
            raise ValueError("Guild and channel IDs must be numeric")
        integration = _integration()
        if pairing.state == DiscordPairing.State.CONSUMED:
            if (
                guild_id != integration.guild_id
                or channel_id != integration.channel_id
                or not capability_matches(
                    actor_capability, integration.inbound_capability_digest
                )
            ):
                return _error(command, "Pairing was already consumed", 409)
            return api_response(
                command=command,
                failed=False,
                result={
                    "installation_id": str(integration.installation_id),
                    "event_capability": decrypt_capability(
                        integration.outbound_capability_ciphertext
                    ),
                },
            )
        if pairing.expires_at <= timezone.now():
            return _error(command, "Pairing is invalid or expired", 404)
        consumed = DiscordPairing.objects.filter(
            pk=pairing.pk, state=DiscordPairing.State.PENDING
        ).update(state=DiscordPairing.State.CONSUMED, consumed_at=timezone.now())
        if consumed != 1:
            return _error(command, "Pairing was already consumed", 409)
        integration.guild_id = guild_id
        integration.guild_name = str(data.get("guild_name") or "")[:128]
        integration.channel_id = channel_id
        integration.channel_name = str(data.get("channel_name") or "")[:128]
        integration.inbound_capability_digest = capability_digest(actor_capability)
        integration.outbound_capability_ciphertext = encrypt_capability(
            event_capability
        )
        # Existing incidents predate this connection and must not flood a newly
        # selected Discord channel. Only events created after pairing are sent.
        integration.delivery_started_at = timezone.now()
        integration.enabled = True
        integration.save()
    except (DiscordPairing.DoesNotExist, KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    return api_response(
        command=command,
        failed=False,
        result={
            "installation_id": str(integration.installation_id),
            "event_capability": event_capability,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def prepare_action(request):
    command = "discord_prepare_action"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        interaction = DiscordInteractionRequest.model_validate(_json_body(request))
        if interaction.operation != "prepare_action":
            raise ValueError("Expected prepare_action operation")
        action = str(interaction.payload["action"])
        _validate_binding(
            integration,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            actor=interaction.actor,
            action=action,
        )
        existing = DiscordPreparedAction.objects.filter(
            interaction_id=interaction.interaction_id
        ).first()
        if existing:
            if (
                str(existing.incident_id) != interaction.incident_id
                or existing.action != action
                or existing.actor.get("discord_id") != interaction.actor.discord_id
            ):
                raise IncidentConflict("Interaction ID was already used")
            if existing.expires_at <= timezone.now():
                raise ValueError("Prepared action has expired")
            token = decrypt_capability(existing.confirmation_ciphertext)
            reason = str(existing.arguments.get("reason") or "").strip()
            prepared = existing
            return api_response(
                command=command,
                failed=False,
                result={
                    "preparation_id": str(prepared.id),
                    "incident_id": str(prepared.incident_id),
                    "incident_revision": prepared.incident_revision,
                    "action": prepared.action,
                    "reason": reason or "-",
                    "preview": prepared.preview,
                    "confirmation_token": token,
                    "requires_second_confirmation": prepared.action
                    in DESTRUCTIVE_ACTIONS,
                    "expires_at": prepared.expires_at,
                    "cached": True,
                },
            )
        incident = get_incident(interaction.incident_id)
        if incident["revision"] != interaction.incident_revision:
            raise IncidentConflict("Incident revision changed")
        arguments = _normalize_action_subject(incident, dict(interaction.payload))
        _validate_prepared_action_target(action, incident, arguments)
        actor_name = (
            f"discord:{interaction.actor.discord_id}:{interaction.actor.display_name}"[
                :150
            ]
        )
        if incident["assigned_to"] and incident["assigned_to"] != actor_name:
            raise IncidentConflict("Incident is already claimed by another moderator")
        if incident["status"] == "new":
            incident = mutate_incident(
                interaction.incident_id,
                actor=actor_name,
                expected_revision=interaction.incident_revision,
                operation="claim",
                idempotency_key=f"claim:{interaction.interaction_id}"[:64],
            )
        reason = str(interaction.payload.get("reason") or "").strip()
        if action in DESTRUCTIVE_ACTIONS and not reason:
            raise ValueError("Destructive actions require a reason")
        token = secrets.token_urlsafe(48)
        preview_target = (
            incident.get("reporter_name")
            if arguments.get("reporter_action") is True
            else _selected_subject_name(incident, arguments)
        ) or "selected subject"
        preview = (
            f"{action} on {preview_target}: "
            f"{reason or interaction.payload.get('message') or ''}"
        )[:2000]
        prepared = DiscordPreparedAction.objects.create(
            incident_id=interaction.incident_id,
            incident_revision=incident["revision"],
            interaction_id=interaction.interaction_id,
            action=action,
            actor=interaction.actor.model_dump(mode="json"),
            arguments=arguments,
            confirmation_digest=capability_digest(token),
            confirmation_ciphertext=encrypt_capability(token),
            preview=preview,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(
        command=command,
        failed=False,
        result={
            "preparation_id": str(prepared.id),
            "incident_id": str(prepared.incident_id),
            "incident_revision": prepared.incident_revision,
            "action": prepared.action,
            "reason": reason or "-",
            "preview": prepared.preview,
            "confirmation_token": token,
            "requires_second_confirmation": action in DESTRUCTIVE_ACTIONS,
            "expires_at": prepared.expires_at,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def select_incident_subject(request):
    """Validate a Discord target selection without changing incident state."""

    command = "discord_incident_select_subject"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        interaction = DiscordInteractionRequest.model_validate(_json_body(request))
        if interaction.operation != "select_subject":
            raise ValueError("Expected select_subject operation")
        _validate_binding(
            integration,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            actor=interaction.actor,
        )
        cached = DiscordInteractionReceipt.objects.filter(
            interaction_id=interaction.interaction_id
        ).first()
        if cached:
            return api_response(command=command, failed=False, result=cached.result)
        incident = get_incident(interaction.incident_id)
        if int(incident["revision"]) != interaction.incident_revision:
            raise IncidentConflict("Incident revision changed")
        subject_id = str(interaction.payload.get("subject_id") or "").strip()
        subject = next(
            (
                item
                for item in incident.get("subjects") or []
                if str(item.get("id") or "") == subject_id
                and item.get("state") == "confirmed"
                and item.get("kind") in {"player", "squad"}
            ),
            None,
        )
        if not subject:
            raise ValueError("Select a confirmed incident subject")
        result = _json_safe(
            {
                "incident_id": interaction.incident_id,
                "incident_revision": incident["revision"],
                "subject_id": subject_id,
                "display_name": (
                    subject.get("squad_name") or subject.get("display_name") or "-"
                ),
            }
        )
        DiscordInteractionReceipt.objects.create(
            interaction_id=interaction.interaction_id,
            operation="select_subject",
            result=result,
        )
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@require_http_methods(["POST"])
def transition_incident(request):
    command = "discord_incident_transition"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        interaction = DiscordInteractionRequest.model_validate(_json_body(request))
        if interaction.operation not in {"claim", "unclaim", "resolve", "dismiss"}:
            raise ValueError("Unsupported Discord incident transition")
        _validate_binding(
            integration,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            actor=interaction.actor,
        )
        cached = DiscordInteractionReceipt.objects.filter(
            interaction_id=interaction.interaction_id
        ).first()
        if cached:
            return api_response(command=command, failed=False, result=cached.result)
        actor_name = (
            f"discord:{interaction.actor.discord_id}:{interaction.actor.display_name}"
        )[:150]
        operation = {
            "resolve": "resolved",
            "dismiss": "dismissed",
        }.get(interaction.operation, interaction.operation)
        result = mutate_incident(
            interaction.incident_id,
            actor=actor_name,
            expected_revision=interaction.incident_revision,
            operation=operation,
            payload=interaction.payload,
            idempotency_key=f"discord:{interaction.interaction_id}"[:64],
        )
        result = _json_safe(result)
        DiscordInteractionReceipt.objects.create(
            interaction_id=interaction.interaction_id,
            operation=interaction.operation,
            result=result,
        )
        template_key = {
            "claim": "claimed",
            "resolve": "resolved",
            "dismiss": "dismissed",
        }.get(interaction.operation)
        template = (integration.reporter_templates or {}).get(
            template_key, DEFAULT_REPORTER_TEMPLATES.get(template_key or "")
        )
        notify_reporter = interaction.payload.get("notify_reporter", True) is not False
        if notify_reporter and template and result.get("reporter_id"):
            try:
                from . import views

                views.rcon_api.message_player(
                    result["reporter_id"],
                    message=template,
                    by=actor_name,
                    save_message=True,
                    player_name=result.get("reporter_name"),
                )
            except Exception:
                # Reporter feedback is best effort and cannot roll back the
                # already committed, audited incident transition.
                pass
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@require_http_methods(["POST"])
def execute_action(request, preparation_id):
    command = "discord_execute_action"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        interaction_id = str(data["interaction_id"])
        if not re.fullmatch(r"[0-9]+", interaction_id):
            raise ValueError("interaction_id must be numeric")
        cached = DiscordInteractionReceipt.objects.filter(
            interaction_id=interaction_id
        ).first()
        if cached:
            return api_response(command=command, failed=False, result=cached.result)
        prepared = DiscordPreparedAction.objects.get(pk=preparation_id)
        actor = DiscordActor.model_validate(data["actor"])
        _validate_binding(
            integration,
            guild_id=str(data["guild_id"]),
            channel_id=str(data["channel_id"]),
            actor=actor,
            action=prepared.action,
        )
        if prepared.actor.get("discord_id") != actor.discord_id:
            raise PermissionError(
                "Only the preparing moderator may confirm this action"
            )
        if prepared.executed_at or prepared.expires_at <= timezone.now():
            raise ValueError("Prepared action is already used or expired")
        if not capability_matches(
            str(data["confirmation_token"]), prepared.confirmation_digest
        ):
            raise PermissionError("Invalid action confirmation")
        incident = get_incident(str(prepared.incident_id))
        actor_name = f"discord:{actor.discord_id}:{actor.display_name}"[:150]
        arguments = _normalize_action_subject(incident, dict(prepared.arguments))
        arguments["discord_actor"] = actor.model_dump(mode="json")
        arguments["confirmed"] = True
        reservation, created = reserve_incident_action(
            str(prepared.incident_id),
            actor=actor_name,
            action=prepared.action,
            arguments=arguments,
            idempotency_key=f"discord:{interaction_id}"[:64],
            confirm_subject_id=str(arguments.get("confirm_subject_id") or "") or None,
            validate_action_subject=True,
        )
        if not created:
            result = {"cached": True, "event": reservation}
        else:
            try:
                action_result = _execute_action(
                    prepared.action, arguments, actor_name, incident
                )
                updated = complete_incident_action(
                    f"discord:{interaction_id}"[:64], result=action_result, error=None
                )
                if (
                    prepared.action != SuggestedAction.MESSAGE.value
                    and _should_auto_resolve_after_action(incident)
                ):
                    try:
                        updated = mutate_incident(
                            str(prepared.incident_id),
                            actor=actor_name,
                            expected_revision=int(updated["revision"]),
                            operation="resolved",
                            payload={
                                "via": "completed_action",
                                "action": prepared.action,
                            },
                            idempotency_key=f"resolve:{interaction_id}"[:64],
                        )
                        template = (integration.reporter_templates or {}).get(
                            "resolved", DEFAULT_REPORTER_TEMPLATES["resolved"]
                        )
                        if template and updated.get("reporter_id"):
                            try:
                                from . import views

                                views.rcon_api.message_player(
                                    updated["reporter_id"],
                                    message=template,
                                    by=actor_name,
                                    save_message=True,
                                    player_name=updated.get("reporter_name"),
                                )
                            except Exception:
                                pass
                    except Exception:
                        # The game action succeeded and is already audited. A
                        # concurrent state update must not report it as failed.
                        pass
            except Exception as exc:
                complete_incident_action(
                    f"discord:{interaction_id}"[:64], error=repr(exc)
                )
                raise
            result = {"action_result": action_result, "incident": updated}
        result = _json_safe(result)
        prepared.executed_at = timezone.now()
        prepared.execution_result = result
        prepared.save(update_fields=["executed_at", "execution_result"])
        DiscordInteractionReceipt.objects.create(
            interaction_id=interaction_id, operation="execute_action", result=result
        )
    except DiscordPreparedAction.DoesNotExist:
        return _error(command, "Prepared action not found", 404)
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except (IncidentNotFound, KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except Exception as exc:
        return _error(command, repr(exc), 502)
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@require_http_methods(["POST"])
def moderation_feedback(request):
    command = "discord_moderation_feedback"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        feedback = ModerationFeedback.model_validate(data["feedback"])
        _validate_binding(
            integration,
            guild_id=str(data["guild_id"]),
            channel_id=str(data["channel_id"]),
            actor=feedback.actor,
        )
        defaults = {
            "incident_id": feedback.incident_id,
            "analysis_id": feedback.analysis_id,
            "actor": feedback.actor.model_dump(mode="json"),
            "decision": feedback.decision,
            "actual_action": feedback.actual_action.value,
            "reason": feedback.reason or "",
        }
        feedback_id = data.get("feedback_id")
        if feedback_id:
            item, created = DiscordModerationFeedback.objects.get_or_create(
                id=feedback_id, defaults=defaults
            )
        else:
            item = DiscordModerationFeedback.objects.create(**defaults)
            created = True
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(
        command=command,
        failed=False,
        result={"feedback_id": str(item.id), "created": created},
    )


@csrf_exempt
@require_http_methods(["POST"])
def moderation_result(request):
    command = "discord_moderation_result"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        if str(data["installation_id"]) != str(integration.installation_id):
            raise PermissionError("Installation does not match capability")
        analysis = ModerationAnalysis.model_validate(data["analysis"])
        policy = ModerationPolicy.model_validate(data.get("policy") or {})
        if data.get("job_id"):
            incident, visibility, created = persist_candidate_analysis(
                analysis_id=str(data["analysis_id"]),
                job_id=str(data["job_id"]),
                analysis=analysis,
            )
        else:
            incident, created = persist_analysis(
                analysis_id=str(data["analysis_id"]),
                incident_id=str(data["incident_id"]),
                analysis=analysis,
                policy=policy,
            )
            visibility = "incident"
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    except Exception as exc:
        if isinstance(
            exc, (KeyError, TypeError, ValueError)
        ) or exc.__class__.__module__.startswith("pydantic"):
            return _error(command, str(exc), 400)
        raise
    return api_response(
        command=command,
        failed=False,
        result={
            "analysis_id": str(data["analysis_id"]),
            "created": created,
            "incident": incident,
            "visibility": visibility,
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def integration_usage(request):
    command = "discord_report_usage"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    if not integration.enabled or not integration.outbound_capability_ciphertext:
        return _error(command, "Discord integration is not connected", 409)
    try:
        response = requests.get(
            (
                f"{integration.service_url.rstrip('/')}/v1/usage/"
                f"{integration.installation_id}"
            ),
            headers={
                "Authorization": (
                    f"Bearer {decrypt_capability(integration.outbound_capability_ciphertext)}"
                )
            },
            timeout=5,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"Discord service unavailable: {exc}", 503)
    result["provider"] = {
        **DEFAULT_AI_CONFIG, **(integration.ai_config or {})
    }.get("provider", "managed")
    return api_response(command=command, failed=False, result=result)


def _ai_service_request(integration, method: str, path: str):
    if not integration.enabled or not integration.outbound_capability_ciphertext:
        raise ValueError("Discord integration is not connected")
    response = requests.request(
        method,
        (
            f"{integration.service_url.rstrip('/')}/v1/ai/"
            f"{integration.installation_id}/{path}"
        ),
        headers={
            "Authorization": (
                f"Bearer {decrypt_capability(integration.outbound_capability_ciphertext)}"
            )
        },
        timeout=35,
    )
    if not response.ok:
        raise requests.RequestException(
            _service_error(response, "AI provider request failed"), response=response
        )
    return response.json()


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def ai_provider_status(request):
    command = "discord_ai_provider_status"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    try:
        result = _ai_service_request(integration, "GET", "status")
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"AI provider unavailable: {exc}", 503)
    result["api_models"] = list(API_MODEL_OPTIONS)
    result["has_api_key"] = bool(integration.ai_api_key_ciphertext)
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def ai_provider_login(request):
    command = "discord_ai_provider_login"
    if denied := _require_manager(request, command):
        return denied
    try:
        result = _ai_service_request(_integration(), "POST", "login")
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"ChatGPT login unavailable: {exc}", 503)
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def ai_provider_logout(request):
    command = "discord_ai_provider_logout"
    if denied := _require_manager(request, command):
        return denied
    try:
        result = _ai_service_request(_integration(), "POST", "logout")
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"ChatGPT logout unavailable: {exc}", 503)
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def test_message(request):
    command = "discord_report_test"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    if not integration.enabled or not integration.outbound_capability_ciphertext:
        return _error(command, "Discord integration is not connected", 409)
    try:
        response = requests.post(
            f"{integration.service_url.rstrip('/')}/v1/test-messages",
            headers={
                "Authorization": (
                    f"Bearer {decrypt_capability(integration.outbound_capability_ciphertext)}"
                )
            },
            json={"installation_id": str(integration.installation_id)},
            timeout=5,
        )
        response.raise_for_status()
    except (requests.RequestException, ValueError) as exc:
        return _error(command, f"Discord service unavailable: {exc}", 503)
    return api_response(command=command, failed=False, result={"sent": True})
