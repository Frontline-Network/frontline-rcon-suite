"""CRCON-side Discord Report Bot configuration and interaction boundary."""

from __future__ import annotations

import json
import math
import os
import re
import secrets
from datetime import timedelta
from datetime import timezone as datetime_timezone
from urllib.parse import urlsplit

import requests
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from sqlalchemy import case, func, select

from rcon.admin_incidents import (
    IncidentConflict,
    IncidentNotFound,
    complete_incident_action,
    confirmed_action_subject,
    get_incident,
    mutate_incident,
    reserve_incident_action,
)
from rcon.incident_notifications import notify_incident_reporter
from rcon.message_templates import get_message_templates
from rcon.models import AdminIncidentDiscordDelivery, enter_session
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
from rcon.utils import get_server_number

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
from .mobile_incidents import (
    DISCORD_GAME_ACTIONS,
    PUNISH_MESSAGE_FALLBACK_OUTCOME,
    _execute_action,
)
from .multi_servers import forward_mobile_request_to_server
from .models import (
    DiscordInteractionReceipt,
    DiscordModerationFeedback,
    DiscordPairing,
    DiscordPreparedAction,
    DiscordReportIntegration,
)

# The Discord UI must only expose actions for which CRCON has a validated
# execution handler. New SuggestedAction values remain unavailable to Discord
# until they are deliberately added to this CRCON-side contract and its tests.
ALL_ACTIONS = set(DISCORD_GAME_ACTIONS)
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
    "provider": "api_key",
    "ai_model": "gpt-5.6-luna",
    "player_name_model": "gpt-5.4-nano",
}
AI_PROVIDERS = {"api_key", "codex"}
API_MODEL_OPTIONS = (
    {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano"},
    {"id": "gpt-5.6-luna", "name": "GPT-5.6 Luna"},
    {"id": "gpt-5.6-terra", "name": "GPT-5.6 Terra"},
    {"id": "gpt-5.6-sol", "name": "GPT-5.6 Sol"},
)
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


def _used_punish_message_fallback(action_result) -> bool:
    return (
        isinstance(action_result, dict)
        and action_result.get("outcome") == PUNISH_MESSAGE_FALLBACK_OUTCOME
        and action_result.get("message_sent") is True
        and action_result.get("punished") is False
    )


SQUAD_LEADER_ROLES = {
    "officer",
    "squadleader",
    "tankcommander",
    "spotter",
    "artilleryobserver",
    "mortarobserver",
    "helicopterlogisticsofficer",
}

DISCORD_PAIRING_CALLBACK_PATH = "/api/discord/v1/pairings/complete"


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


def _pairing_callback_url(request, installation_id=None) -> str:
    """Return the externally reachable HTTPS callback behind reverse proxies.

    ``request.build_absolute_uri`` reflects the internal HTTP hop when CRCON is
    deployed behind the usual host Nginx and frontend container. The mobile
    public base URL is already the installation's validated, operator-managed
    HTTPS address, so it is also the authoritative Discord callback origin.
    """

    callback_base_url = os.getenv("DISCORD_CALLBACK_BASE_URL", "").strip().rstrip("/")
    if callback_base_url and installation_id:
        try:
            parsed = urlsplit(callback_base_url)
            port = parsed.port
        except ValueError:
            parsed = None
            port = None
        if (
            parsed is not None
            and parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and port in {None, 443}
            and parsed.path in {"", "/"}
        ):
            return (
                f"{callback_base_url}/v1/installations/{installation_id}"
                f"{DISCORD_PAIRING_CALLBACK_PATH}"
            )

    public_base_url = os.getenv("MOBILE_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base_url:
        try:
            parsed = urlsplit(public_base_url)
            port = parsed.port
        except ValueError:
            parsed = None
            port = None
        if (
            parsed is not None
            and parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
            and port in {None, 443}
            and parsed.path in {"", "/"}
        ):
            return f"{public_base_url}{DISCORD_PAIRING_CALLBACK_PATH}"
    return request.build_absolute_uri(DISCORD_PAIRING_CALLBACK_PATH)


def _new_pairing(request) -> tuple[DiscordPairing, str, dict]:
    DiscordPairing.objects.filter(state=DiscordPairing.State.PENDING).delete()
    secret = new_capability("pair")
    pairing = DiscordPairing.objects.create(
        secret_digest=capability_digest(secret),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    integration = _integration()
    payload = {
        "crcon_callback_url": _pairing_callback_url(
            request, getattr(integration, "installation_id", None)
        ),
        "pairing_id": str(pairing.id),
        "pairing_secret": secret,
        "installation_id": str(integration.installation_id),
    }
    return pairing, secret, payload


def _service_error(response, fallback: str) -> str:
    """Expose the central service's safe API detail, not a generic HTTP error."""

    try:
        detail = response.json().get("detail")
    except (AttributeError, TypeError, ValueError):
        detail = None
    return str(detail)[:500] if detail else fallback


def _normalized_ai_config(raw_config: dict | None) -> dict:
    config = {**DEFAULT_AI_CONFIG, **(raw_config or {})}
    if config.get("provider") not in AI_PROVIDERS:
        # Never let a legacy `managed` installation fall back to Frontline's
        # OpenAI project. Ordinary reports remain available, but AI jobs stay
        # disabled until the customer explicitly configures a provider.
        config.update(
            provider="api_key",
            chat_enabled=False,
            names_enabled=False,
        )
    return config


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
        "ai_config": _normalized_ai_config(integration.ai_config),
        "has_api_key": bool(integration.ai_api_key_ciphertext),
        "api_model_options": list(API_MODEL_OPTIONS),
        "policy": integration.policy,
        "reporter_templates": {
            **DEFAULT_REPORTER_TEMPLATES,
            **(integration.reporter_templates or {}),
        },
    }


def _safe_error_code(value: object, fallback: str = "unknown_error") -> str:
    normalized = re.sub(r"[^a-z0-9_.:=-]+", "_", str(value or "").casefold())
    return (normalized.strip("_") or fallback)[:128]


def _delivery_summary() -> dict:
    """Return content-free outbox health without triggering any network work."""

    try:
        with enter_session() as session:
            last_delivered_at, last_attempt_at, pending_count = session.execute(
                select(
                    func.max(AdminIncidentDiscordDelivery.delivered_at),
                    func.max(AdminIncidentDiscordDelivery.updated_at),
                    func.coalesce(
                        func.sum(
                            case(
                                (
                                    AdminIncidentDiscordDelivery.delivered_at.is_(None),
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                )
            ).one()
            latest_error = session.execute(
                select(AdminIncidentDiscordDelivery.last_error)
                .where(AdminIncidentDiscordDelivery.last_error.is_not(None))
                .order_by(AdminIncidentDiscordDelivery.updated_at.desc())
                .limit(1)
            ).scalar_one_or_none()
    except Exception:
        return {
            "state": "unknown",
            "last_delivered_at": None,
            "last_attempt_at": None,
            "pending_count": None,
            "error_code": "outbox_status_unavailable",
        }

    pending_count = int(pending_count or 0)
    if pending_count and latest_error:
        state = "retrying"
    elif pending_count:
        state = "pending"
    elif last_delivered_at:
        state = "delivered"
    else:
        state = "idle"
    return {
        "state": state,
        "last_delivered_at": last_delivered_at,
        "last_attempt_at": last_attempt_at,
        "pending_count": pending_count,
        "error_code": _safe_error_code(latest_error) if pending_count else None,
    }


def _operational_status(integration: DiscordReportIntegration) -> dict:
    connected = bool(
        integration.guild_id
        and integration.channel_id
        and integration.inbound_capability_digest
        and integration.outbound_capability_ciphertext
    )
    if not connected:
        setup_state = "not_connected"
    elif not integration.enabled:
        setup_state = "paused"
    else:
        setup_state = "active"
    callback_base = os.getenv("DISCORD_CALLBACK_BASE_URL", "").strip().rstrip("/")
    return {
        "setup_state": setup_state,
        "enabled": integration.enabled,
        "connected": connected,
        "service_configured": integration.service_url.startswith("https://"),
        "callback_mode": (
            "broker" if callback_base.startswith("https://") else "direct"
        ),
        "delivery": _delivery_summary(),
        "last_test": {
            "state": (
                "unknown"
                if integration.last_test_success is None
                else "succeeded" if integration.last_test_success else "failed"
            ),
            "checked_at": integration.last_test_at,
            "error_code": integration.last_test_error or None,
        },
        "last_diagnostic": {
            "checked_at": integration.last_diagnostic_at,
            "result": integration.last_diagnostic_result or None,
        },
    }


def _remote_error_code(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return _safe_error_code(
        f"http_{status_code}" if isinstance(status_code, int) else type(exc).__name__
    )


def _normalized_diagnostic_result(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Invalid diagnostics response")
    if str(raw.get("state")) not in {"healthy", "degraded"}:
        raise ValueError("Invalid diagnostics state")
    checked_at = parse_datetime(str(raw.get("checked_at") or ""))
    if checked_at is None or not timezone.is_aware(checked_at):
        raise ValueError("Invalid diagnostics timestamp")
    result = {
        "state": str(raw["state"]),
        "checked_at": checked_at.astimezone(datetime_timezone.utc).isoformat(),
    }
    for key in ("service", "discord_binding", "callback"):
        component = dict(raw.get(key) or {})
        state = str(component.get("state") or "unknown")
        if state not in {"online", "offline", "unknown"}:
            raise ValueError("Invalid diagnostics component state")
        normalized = {"state": state}
        if component.get("error_code") is not None:
            normalized["error_code"] = _safe_error_code(component["error_code"])
        transport = component.get("transport")
        if transport is not None:
            if transport not in {"direct", "broker"}:
                raise ValueError("Invalid diagnostics transport")
            normalized["transport"] = transport
        for id_key in ("guild_id", "channel_id"):
            identifier = component.get(id_key)
            if identifier is not None:
                if not isinstance(identifier, str) or not re.fullmatch(
                    r"[0-9]{1,32}", identifier
                ):
                    raise ValueError("Invalid diagnostics identifier")
                normalized[id_key] = identifier
        for name_key in ("guild_name", "channel_name"):
            name = component.get(name_key)
            if name is not None:
                if not isinstance(name, str):
                    raise ValueError("Invalid diagnostics name")
                normalized[name_key] = name[:128]
        latency = component.get("latency_ms")
        if latency is not None:
            if (
                isinstance(latency, bool)
                or not isinstance(latency, (int, float))
                or not math.isfinite(latency)
            ):
                raise ValueError("Invalid diagnostics latency")
            normalized["latency_ms"] = max(0, min(60_000, round(latency)))
        result[key] = normalized
    return result


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


def _forward_discord_incident_request(
    request, command: str, incident: dict, data: dict
) -> HttpResponse | None:
    """Route game-affecting Discord work to the incident's CRCON profile.

    A multi-server installation has one public Discord callback, normally on
    server 1, while an incident can belong to any game-server profile. The
    incident's persisted server number is authoritative; caller input cannot
    choose another target.
    """

    server_number = int(incident["server_number"])
    if server_number == int(get_server_number()) or data.get("forwarded"):
        return None
    try:
        response = forward_mobile_request_to_server(
            request,
            server_number,
            request.path,
            data=data,
            method=request.method,
        )
    except ValueError as exc:
        return _error(command, str(exc), 503)
    return HttpResponse(
        content=response.content,
        status=response.status_code,
        content_type=response.headers.get("content-type", "application/json"),
    )


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
            and (
                integration.ai_config.get("chat_enabled")
                or integration.ai_config.get("names_enabled")
            )
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
def integration_status(request):
    command = "discord_report_status"
    if denied := _require_manager(request, command):
        return denied
    return api_response(
        command=command,
        failed=False,
        result=_operational_status(_integration()),
    )


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def run_integration_diagnostics(request):
    command = "discord_report_diagnostics"
    if denied := _require_manager(request, command):
        return denied
    integration = _integration()
    if not integration.outbound_capability_ciphertext:
        return _error(command, "Discord integration is not connected", 409)

    checked_at = timezone.now()
    try:
        response = requests.post(
            f"{integration.service_url.rstrip('/')}/v1/diagnostics",
            headers={
                "Authorization": (
                    f"Bearer {decrypt_capability(integration.outbound_capability_ciphertext)}"
                )
            },
            json={"installation_id": str(integration.installation_id)},
            timeout=12,
        )
        response.raise_for_status()
        result = _normalized_diagnostic_result(response.json())
    except (requests.RequestException, TypeError, ValueError) as exc:
        result = {
            "state": "degraded",
            "checked_at": checked_at.isoformat(),
            "service": {"state": "offline", "error_code": _remote_error_code(exc)},
            "discord_binding": {"state": "unknown"},
            "callback": {"state": "unknown"},
        }
        integration.last_diagnostic_at = checked_at
        integration.last_diagnostic_result = result
        integration.save(
            update_fields=[
                "last_diagnostic_at",
                "last_diagnostic_result",
                "updated_at",
            ]
        )
        return _error(command, "Discord diagnostics could not be completed", 503)

    integration.last_diagnostic_at = checked_at
    integration.last_diagnostic_result = result
    integration.save(
        update_fields=["last_diagnostic_at", "last_diagnostic_result", "updated_at"]
    )
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@require_http_methods(["POST"])
def diagnostic_callback_ping(request):
    command = "discord_report_diagnostic_ping"
    integration, denied = _authorized_integration(request, command)
    if denied:
        return denied
    try:
        data = _json_body(request)
        if str(data.get("installation_id") or "") != str(integration.installation_id):
            raise ValueError("Installation does not match capability")
    except (TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    return api_response(
        command=command,
        failed=False,
        result={
            "installation_id": str(integration.installation_id),
            "received_at": timezone.now(),
        },
    )


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
    pairing, secret, pairing_payload = _new_pairing(request)
    try:
        response = requests.post(
            f"{integration.service_url.rstrip('/')}/v1/install-intents",
            json=pairing_payload,
            timeout=15,
        )
        if not response.ok:
            return _error(
                command,
                _service_error(response, "Discord installation could not be started"),
                response.status_code if 400 <= response.status_code < 500 else 503,
            )
        install_url = str(response.json()["install_url"])
        if not install_url.startswith("https://discord.com/"):
            raise ValueError("Discord service returned an invalid install URL")
    except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
        return _error(command, f"Discord installation could not be started: {exc}", 503)
    return api_response(
        command=command,
        failed=False,
        result={
            "pairing_id": str(pairing.id),
            "pairing_secret": secret,
            "expires_at": pairing.expires_at,
            "install_url": install_url,
            "service_url": integration.service_url,
            "crcon_callback_url": _pairing_callback_url(
                request, integration.installation_id
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
        data = _json_body(request)
        # ``forwarded`` is an internal multi-server transport marker, not part
        # of the public Discord interaction contract. Keep it available for
        # loop prevention while validating only the signed interaction data.
        interaction_data = dict(data)
        interaction_data.pop("forwarded", None)
        interaction = DiscordInteractionRequest.model_validate(interaction_data)
        if interaction.operation not in {"claim", "unclaim", "resolve", "dismiss", "cancel_leadership_vote"}:
            raise ValueError("Unsupported Discord incident transition")
        _validate_binding(
            integration,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            actor=interaction.actor,
        )
        incident = get_incident(interaction.incident_id)
        forwarded = _forward_discord_incident_request(
            request, command, incident, data
        )
        if forwarded is not None:
            return forwarded
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
        if notify_reporter and template:
            try:
                from . import views

                notify_incident_reporter(
                    views.rcon_api,
                    result,
                    message=template,
                    by=actor_name,
                    save_message=True,
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
        forwarded = _forward_discord_incident_request(
            request, command, incident, data
        )
        if forwarded is not None:
            return forwarded
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
                    and not _used_punish_message_fallback(action_result)
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
                        if template:
                            try:
                                from . import views

                                notify_incident_reporter(
                                    views.rcon_api,
                                    updated,
                                    message=template,
                                    by=actor_name,
                                    save_message=True,
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
    result["provider"] = _normalized_ai_config(integration.ai_config)["provider"]
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
    if not integration.outbound_capability_ciphertext:
        return _error(command, "Discord integration is not connected", 409)
    checked_at = timezone.now()
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
        integration.last_test_at = checked_at
        integration.last_test_success = False
        integration.last_test_error = _remote_error_code(exc)
        integration.save(
            update_fields=[
                "last_test_at",
                "last_test_success",
                "last_test_error",
                "updated_at",
            ]
        )
        return _error(command, "Discord test message could not be delivered", 503)
    integration.last_test_at = checked_at
    integration.last_test_success = True
    integration.last_test_error = ""
    integration.save(
        update_fields=[
            "last_test_at",
            "last_test_success",
            "last_test_error",
            "updated_at",
        ]
    )
    return api_response(command=command, failed=False, result={"sent": True})
