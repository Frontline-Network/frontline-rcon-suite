from __future__ import annotations
import hashlib

import copy
import ipaddress
import re
import secrets
import socket
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic, time
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import InvalidToken
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .ai import CodexAnalyzer, ManagedAnalyzer, PlayerNameBatchInput
from .codex_runtime import (
    CodexRuntimeError,
)
from .codex_runtime import account_status as codex_account_status
from .codex_runtime import logout as codex_logout
from .codex_runtime import (
    start_device_login,
)
from .config import get_settings
from .contracts import (
    IncidentEventEnvelope,
    ModerationAnalysisJobEnvelope,
    ModerationPolicy,
    ModerationSource,
    PlayerNameAnalysisBatchEnvelope,
)
from .db import Base, engine, session_dependency
from .discord_client import DiscordClient, render_message
from .models import (
    EventReceipt,
    IncidentMessage,
    InstallationGuildBinding,
    Integration,
    OAuthInstallIntent,
    PreparedActionRelay,
    TechnicalUsageMetric,
)
from .security import decrypt, derive_capability, digest, encrypt, matches

Base.metadata.create_all(engine)
app = FastAPI(title="Frontline CRCON Discord Service", version="1.0.0")
_rate_windows: dict[str, tuple[float, int]] = {}
_rate_lock = Lock()


def _check_rate_limit(key: str):
    now = monotonic()
    with _rate_lock:
        started, count = _rate_windows.get(key, (now, 0))
        if started <= now - 60:
            started, count = now, 0
        if count >= get_settings().rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _rate_windows[key] = (started, count + 1)
        if len(_rate_windows) > 10000:
            expired = [
                item_key
                for item_key, (item_started, _) in _rate_windows.items()
                if item_started <= now - 60
            ]
            for item_key in expired:
                _rate_windows.pop(item_key, None)


class PairingDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crcon_callback_url: HttpUrl
    pairing_id: str = Field(min_length=1, max_length=36)
    pairing_secret: str = Field(min_length=32, max_length=255)
    installation_id: str | None = Field(default=None, min_length=1, max_length=64)


class PairingRequest(PairingDiscoveryRequest):
    channel_id: str = Field(pattern=r"^[0-9]+$", max_length=32)
    channel_name: str = Field(default="", max_length=128)


class DiagnosticsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    installation_id: str = Field(min_length=1, max_length=64)


def _bearer(authorization: str | None) -> str:
    return (
        authorization[7:]
        if authorization and authorization.startswith("Bearer ")
        else ""
    )


def _crcon_post(url: str, **kwargs):
    """POST to CRCON, authenticating the central broker when its URL is used."""

    settings = get_settings()
    broker_url = settings.callback_broker_url.strip().rstrip("/")
    headers = dict(kwargs.pop("headers", {}) or {})
    if broker_url and (url == broker_url or url.startswith(f"{broker_url}/")):
        if not settings.callback_broker_token:
            raise httpx.RequestError("Callback broker capability is not configured")
        headers["X-Frontline-Broker-Authorization"] = (
            f"Bearer {settings.callback_broker_token}"
        )
    return httpx.post(url, headers=headers, **kwargs)


def _external_error_code(exc: Exception, fallback: str) -> str:
    """Return a stable external-service error code without response content."""

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return f"http_{status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.RequestError):
        return "connection_failed"
    if isinstance(exc, (InvalidToken, UnicodeError)):
        return "capability_invalid"
    return fallback


def _integration_for_event(
    session: Session, envelope: IncidentEventEnvelope, authorization: str | None
) -> Integration:
    integration = session.get(Integration, envelope.installation_id)
    if (
        integration is None
        or not integration.enabled
        or not matches(
            _bearer(authorization), integration.event_capability_digest, "events"
        )
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    return integration


def _integration_for_capability(
    session: Session, installation_id: str, authorization: str | None
) -> Integration:
    integration = session.get(Integration, installation_id)
    if (
        integration is None
        or not integration.enabled
        or not matches(
            _bearer(authorization), integration.event_capability_digest, "events"
        )
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    return integration


def _send_feedback(
    integration: Integration,
    *,
    interaction_id: str,
    guild_id: str,
    channel_id: str,
    incident_id: str,
    analysis_id: str | None,
    actor: dict,
    decision: str,
    actual_action: str,
) -> None:
    if not analysis_id:
        return
    try:
        response = _crcon_post(
            f"{integration.crcon_base_url}/api/discord/v1/moderation-feedback",
            headers={
                "Authorization": (
                    f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                )
            },
            json={
                "feedback_id": str(
                    uuid.uuid5(uuid.NAMESPACE_URL, f"discord-feedback:{interaction_id}")
                ),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "feedback": {
                    "incident_id": incident_id,
                    "analysis_id": analysis_id,
                    "actor": actor,
                    "decision": decision,
                    "actual_action": actual_action,
                },
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Feedback must never roll back an already audited moderation decision.
        return


def _has_local_hard_rule(policy: ModerationPolicy, rule_ids: list[str]) -> bool:
    return bool(policy.hard_rule_ids.intersection(rule_ids))


def _usage_summary(session: Session, installation_id: str) -> dict[str, int]:
    now = datetime.now(tz=timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = int(
        session.execute(
            select(
                func.coalesce(
                    func.sum(
                        TechnicalUsageMetric.input_tokens
                        + TechnicalUsageMetric.output_tokens
                    ),
                    0,
                )
            ).where(
                TechnicalUsageMetric.installation_id == installation_id,
                TechnicalUsageMetric.created_at >= month_start,
            )
        ).scalar_one()
    )
    return {"used_tokens": used}


def _validate_crcon_callback(callback: str) -> None:
    settings = get_settings()
    parsed = urlsplit(callback)
    if settings.dry_run:
        return
    broker_url = settings.callback_broker_url.strip().rstrip("/")
    broker = urlsplit(broker_url) if broker_url else None
    broker_path_ok = bool(
        broker
        and parsed.scheme == broker.scheme
        and parsed.hostname == broker.hostname
        and parsed.port == broker.port
        and re.fullmatch(
            re.escape(broker.path.rstrip("/"))
            + r"/v1/installations/[0-9a-fA-F-]{36}/api/discord/v1/pairings/complete",
            parsed.path,
        )
    )
    direct_path_ok = parsed.path == "/api/discord/v1/pairings/complete"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not (direct_path_ok or broker_path_ok)
        or parsed.port not in {None, 443}
    ):
        raise HTTPException(status_code=400, detail="Invalid CRCON callback URL")
    hostname = parsed.hostname.lower()
    allowed_hosts = settings.crcon_host_allowlist()
    if direct_path_ok and allowed_hosts and hostname not in allowed_hosts:
        raise HTTPException(status_code=400, detail="CRCON host is not allowed")
    try:
        addresses = {
            item[4][0].split("%", 1)[0]
            for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise HTTPException(
            status_code=400, detail="CRCON host cannot be resolved"
        ) from exc
    if not addresses or any(
        not ipaddress.ip_address(address).is_global for address in addresses
    ):
        raise HTTPException(
            status_code=400, detail="CRCON callback must resolve to public addresses"
        )


def _verify_pending_pairing(payload: PairingDiscoveryRequest, callback: str) -> None:
    verify_url = callback.removesuffix("/complete") + "/verify"
    try:
        response = _crcon_post(
            verify_url,
            json={
                "pairing_id": payload.pairing_id,
                "pairing_secret": payload.pairing_secret,
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=400, detail="CRCON pairing is invalid or expired"
        ) from exc


def _single_guild_options(session: Session) -> dict:
    paired_guilds = {
        str(value)
        for value in session.execute(
            select(Integration.guild_id).where(Integration.enabled.is_(True)).distinct()
        ).scalars()
        if value
    }
    preferred_guild_id = next(iter(paired_guilds)) if len(paired_guilds) == 1 else None
    try:
        return DiscordClient().single_guild_options(preferred_guild_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Discord server options are unavailable"
        ) from exc


def _pairing_guild_options(payload: PairingDiscoveryRequest, session: Session) -> dict:
    if payload.installation_id:
        binding = session.get(InstallationGuildBinding, payload.installation_id)
        guild_id = binding.guild_id if binding and binding.authorized else ""
        if not guild_id:
            integration = session.get(Integration, payload.installation_id)
            if integration and integration.enabled:
                guild_id = integration.guild_id
        if guild_id:
            try:
                return DiscordClient().guild_options(guild_id)
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=502, detail="Discord server options are unavailable"
                ) from exc
        raise HTTPException(
            status_code=409,
            detail=(
                "Install the Discord app for this CRCON before detecting its server"
            ),
        )
    return _single_guild_options(session)


def _purge_expired_relays(session: Session) -> None:
    session.execute(
        delete(PreparedActionRelay).where(
            PreparedActionRelay.expires_at <= datetime.now(tz=timezone.utc)
        )
    )


def _crcon_interaction_error(exc: httpx.HTTPError) -> str:
    """Return an honest user-facing error without exposing CRCON internals."""

    if isinstance(exc, httpx.HTTPStatusError):
        try:
            detail = str((exc.response.json() or {}).get("error") or "")
        except (TypeError, ValueError):
            detail = ""
        known_details = {
            "Select a confirmed player before running an action": (
                "Dieser Report hat keinen bestätigten betroffenen Spieler."
            ),
            "Actions require a player from a confirmed incident subject": (
                "Für diese Aktion muss zuerst ein betroffener Spieler bestätigt werden."
            ),
            "Select an affected player before running this action": (
                "Dieser Report hat keinen betroffenen Spieler."
            ),
            "Incident is already closed": "Dieser Incident ist bereits abgeschlossen.",
            "Only open incidents can be claimed": (
                "Dieser Incident ist bereits abgeschlossen."
            ),
            "Incident is already claimed by another admin": (
                "⛔ Dieser Report wird bereits von einem anderen Administrator bearbeitet."
            ),
            "The game server rejected the action; the incident remains open": (
                "Der Gameserver hat die Aktion abgelehnt. Der Report bleibt offen."
            ),
        }
        if detail in known_details:
            return known_details[detail]
        if exc.response.status_code == 502 and (
            "HLLCommandError" in detail or "HLLCommandFailedError" in detail
        ):
            return (
                "Der Gameserver konnte die Ausführung nicht bestätigen. "
                "Die Aktion kann im Spiel verzögert erscheinen; bitte nicht sofort "
                "erneut ausführen. Der Report bleibt offen."
            )
        return {
            400: "CRCON hat die Interaktion als ungültig abgelehnt.",
            403: "Du hast keine aktuell erlaubte Discord-Moderatorrolle.",
            404: "Incident oder Discord-Integration wurde nicht gefunden.",
            409: "Der Incident wurde bereits geändert. Bitte nutze die aktualisierte Nachricht.",
        }.get(exc.response.status_code, "CRCON hat die Interaktion abgelehnt.")
    return "CRCON ist derzeit nicht erreichbar."


PUNISH_MESSAGE_FALLBACK_OUTCOME = "punish_not_confirmed_message_sent"


def _execute_prepared_action(
    integration: Integration,
    *,
    preparation_id: str,
    confirmation_token: str,
    interaction_id: str,
    guild_id: str,
    channel_id: str,
    actor: dict,
) -> dict:
    response = _crcon_post(
        f"{integration.crcon_base_url}/api/discord/v1/actions/{preparation_id}/execute",
        headers={
            "Authorization": (
                f"Bearer {decrypt(integration.action_capability_ciphertext)}"
            )
        },
        json={
            "interaction_id": interaction_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "actor": actor,
            "confirmation_token": confirmation_token,
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", payload) if isinstance(payload, dict) else {}
    return result if isinstance(result, dict) else {}


def _action_execution_message(result: dict, action: str) -> str:
    action_result = result.get("action_result")
    if (
        action == "punish"
        and isinstance(action_result, dict)
        and action_result.get("outcome") == PUNISH_MESSAGE_FALLBACK_OUTCOME
        and action_result.get("message_sent") is True
        and action_result.get("punished") is False
    ):
        return (
            "Der Gameserver konnte die Bestrafung nicht bestätigen. Der Spieler "
            "war möglicherweise bereits tot. Der Bestrafungsgrund wurde ihm "
            "stattdessen als Nachricht gesendet; der Report bleibt offen."
        )
    if action == "message":
        return (
            "Nachricht wurde vom Gameserver angenommen. Die Anzeige im Spiel "
            "kann sich insbesondere bei HLL Vietnam verzögern."
        )
    return "Aktion wurde in CRCON ausgeführt und protokolliert."


def _action_modal(
    incident_id: str,
    revision: str,
    action: str,
    *,
    initial_text: str = "",
    duration_hours: int = 2,
) -> dict:
    text_key = "message" if action in {"message", "message_reporter"} else "reason"
    inputs = [
        {
            "type": 1,
            "components": [
                {
                    "type": 4,
                    "custom_id": text_key,
                    "label": "Nachricht" if text_key == "message" else "Grund",
                    "style": 2,
                    "required": True,
                    "min_length": 1 if text_key == "message" else 3,
                    "max_length": 1000,
                    **({"value": initial_text[:1000]} if initial_text else {}),
                }
            ],
        }
    ]
    if action == "temp_ban":
        inputs.append(
            {
                "type": 1,
                "components": [
                    {
                        "type": 4,
                        "custom_id": "duration_hours",
                        "label": "Dauer in Stunden (1-720)",
                        "style": 1,
                        "required": True,
                        "value": str(duration_hours),
                        "max_length": 3,
                    }
                ],
            }
        )
    return {
        "type": 9,
        "data": {
            "custom_id": f"action-modal:{incident_id}:{revision}:{action}",
            "title": (
                "Aktion prüfen und vorbereiten"
                if action in {"perma_ban", "blacklist", "disband_squad"}
                else "Aktion ausführen"
            ),
            "components": inputs,
        },
    }


def _template_picker(
    incident_id: str, revision: str, action: str, templates: list[dict]
) -> dict:
    options = [
        {
            "label": str(item.get("title") or f"Vorlage {item.get('id')}")[:100],
            "value": str(item["id"]),
        }
        for item in templates[:24]
    ]
    options.append({"label": "Freitext", "value": "custom", "emoji": {"name": "✍️"}})
    return {
        "type": 4,
        "data": {
            "content": "Wähle eine CRCON-Vorlage oder öffne ein leeres Freitextfeld.",
            "flags": 64,
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": f"template:{incident_id}:{revision}:{action}",
                            "placeholder": "CRCON-Vorlage auswählen",
                            "min_values": 1,
                            "max_values": 1,
                            "options": options,
                        }
                    ],
                }
            ],
        },
    }


def _claim_from_first_button(
    integration: Integration,
    *,
    interaction_id: str,
    guild_id: str,
    channel_id: str,
    incident_id: str,
    revision: int,
    actor: dict,
    payload: dict | None = None,
) -> dict:
    response = _crcon_post(
        f"{integration.crcon_base_url}/api/discord/v1/incidents/transition",
        headers={
            "Authorization": (
                f"Bearer {decrypt(integration.action_capability_ciphertext)}"
            )
        },
        json={
            "interaction_id": interaction_id,
            "installation_id": integration.installation_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "incident_id": incident_id,
            "incident_revision": revision,
            "actor": actor,
            "operation": "claim",
            "payload": payload or {"via": "first_button"},
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("result", response.json())


def _confirmed_squad_subject_ids(incident: dict) -> set[str]:
    return {
        str(subject.get("id"))
        for subject in incident.get("subjects") or []
        if subject.get("id")
        and subject.get("kind") == "squad"
        and subject.get("state") == "confirmed"
    }


def _message_selection_update(
    message: dict, *, subject_id: str, display_name: str
) -> dict:
    """Return a safe Discord message update with a globally visible selection."""

    embeds = copy.deepcopy(message.get("embeds") or [])[:10]
    components = copy.deepcopy(message.get("components") or [])[:5]
    for embed in embeds:
        # Discord includes response-only metadata in interaction payloads.
        # It must not be echoed back in an Update Message response.
        embed.pop("type", None)
    for row in components:
        row.pop("id", None)
        for component in row.get("components") or []:
            component.pop("id", None)
    valid_option = False
    for row in components:
        for component in row.get("components") or []:
            if component.get("type") != 3 or not str(
                component.get("custom_id") or ""
            ).startswith("subject:"):
                continue
            for option in component.get("options") or []:
                selected = str(option.get("value") or "") == subject_id
                option["default"] = selected
                valid_option = valid_option or selected
    if not valid_option:
        raise ValueError("The selected subject is not available in this message")
    if embeds:
        fields = embeds[0].setdefault("fields", [])
        selection_field = next(
            (
                field
                for field in fields
                if str(field.get("name") or "").startswith("🎯")
            ),
            None,
        )
        language_is_german = bool(
            selection_field and "Zielauswahl" in str(selection_field.get("name") or "")
        )
        value = (
            f"Ausgewählt: **{display_name}**"
            if language_is_german
            else f"Selected: **{display_name}**"
        )
        if selection_field:
            selection_field["value"] = value
        elif len(fields) < 25:
            fields.append(
                {
                    "name": "🎯 Zielauswahl",
                    "value": f"Ausgewählt: **{display_name}**",
                    "inline": False,
                }
            )
    return {
        "embeds": embeds,
        "components": components,
        "allowed_mentions": {"parse": []},
    }


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        # This key is only the zero-cost Omni moderation gate for subscription
        # chat checks, never a Frontline-funded generative analysis provider.
        "ai_configured": bool(get_settings().openai_api_key),
    }


@app.get("/v1/options/{installation_id}")
def discord_options(
    installation_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    integration = session.get(Integration, installation_id)
    if (
        integration is None
        or not integration.enabled
        or not matches(
            _bearer(authorization), integration.event_capability_digest, "events"
        )
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    _check_rate_limit(f"options:{installation_id}")
    try:
        return DiscordClient().guild_options(integration.guild_id)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="Discord server options are unavailable"
        ) from exc


@app.post("/v1/diagnostics")
def integration_diagnostics(
    payload: DiagnosticsRequest,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    """Run an explicit, content-free Discord and callback round-trip check."""

    integration = _integration_for_capability(
        session, payload.installation_id, authorization
    )
    _check_rate_limit(f"diagnostics:{integration.installation_id}")
    checked_at = datetime.now(tz=timezone.utc)

    discord_started = monotonic()
    try:
        options = DiscordClient().guild_options(integration.guild_id)
        channel = next(
            (
                item
                for item in options.get("channels", [])
                if str(item.get("id")) == integration.channel_id
            ),
            None,
        )
        discord_error_code = "configured_channel_missing" if channel is None else ""
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        discord_error_code = _external_error_code(exc, "invalid_discord_response")
        channel = None

    if channel is None:
        discord_binding = {
            "state": "offline",
            "latency_ms": round((monotonic() - discord_started) * 1000),
            "error_code": discord_error_code,
        }
    else:
        discord_binding = {
            "state": "online",
            "latency_ms": round((monotonic() - discord_started) * 1000),
            "guild_id": integration.guild_id,
            "guild_name": str((options.get("guild") or {}).get("name") or "")[:128],
            "channel_id": integration.channel_id,
            "channel_name": str(channel.get("name") or "")[:128],
        }

    callback_started = monotonic()
    try:
        response = _crcon_post(
            f"{integration.crcon_base_url}/api/discord/v1/diagnostics/ping",
            headers={
                "Authorization": (
                    f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                )
            },
            json={"installation_id": integration.installation_id},
            timeout=5,
        )
        response.raise_for_status()
    except (httpx.HTTPError, InvalidToken, UnicodeError, ValueError) as exc:
        callback = {
            "state": "offline",
            "latency_ms": round((monotonic() - callback_started) * 1000),
            "error_code": _external_error_code(exc, "invalid_callback_response"),
        }
    else:
        callback = {
            "state": "online",
            "latency_ms": round((monotonic() - callback_started) * 1000),
            "transport": (
                "broker"
                if get_settings().callback_broker_url.strip().rstrip("/")
                and integration.crcon_base_url.startswith(
                    f"{get_settings().callback_broker_url.strip().rstrip('/')}/"
                )
                else "direct"
            ),
        }

    healthy = all(
        component["state"] == "online" for component in (discord_binding, callback)
    )
    return {
        "state": "healthy" if healthy else "degraded",
        "checked_at": checked_at,
        "service": {"state": "online"},
        "discord_binding": discord_binding,
        "callback": callback,
    }


@app.get("/oauth/install")
def oauth_install():
    if not get_settings().discord_install_url:
        raise HTTPException(
            status_code=503, detail="Discord install URL is not configured"
        )
    return RedirectResponse(get_settings().discord_install_url, status_code=302)


@app.post("/v1/install-intents", status_code=status.HTTP_201_CREATED)
def create_install_intent(
    payload: PairingDiscoveryRequest,
    session: Session = Depends(session_dependency),
):
    callback = str(payload.crcon_callback_url)
    _check_rate_limit(f"install-intent:{urlsplit(callback).hostname}")
    _validate_crcon_callback(callback)
    _verify_pending_pairing(payload, callback)
    settings = get_settings()
    if not payload.installation_id:
        raise HTTPException(status_code=400, detail="CRCON installation ID is required")
    if not (
        settings.discord_application_id
        and settings.discord_client_secret
        and settings.discord_oauth_redirect_uri.startswith("https://")
    ):
        raise HTTPException(status_code=503, detail="Discord OAuth is not configured")
    raw_state = secrets.token_urlsafe(32)
    state_digest = digest(raw_state, "oauth-state")
    session.add(
        OAuthInstallIntent(
            state_digest=state_digest,
            installation_id=payload.installation_id,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=10),
        )
    )
    session.commit()
    query = urlencode(
        {
            "client_id": settings.discord_application_id,
            "permissions": str(settings.discord_permissions),
            "integration_type": "0",
            "scope": "bot applications.commands identify",
            "response_type": "code",
            "redirect_uri": settings.discord_oauth_redirect_uri,
            "state": raw_state,
            "prompt": "consent",
        }
    )
    return {"install_url": f"https://discord.com/oauth2/authorize?{query}"}


@app.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(
    code: str,
    state: str,
    session: Session = Depends(session_dependency),
):
    settings = get_settings()
    intent = session.get(OAuthInstallIntent, digest(state, "oauth-state"))
    now = datetime.now(tz=timezone.utc)
    expires_at = intent.expires_at if intent is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if intent is None or intent.used_at is not None or expires_at <= now:
        raise HTTPException(status_code=400, detail="Discord installation expired")
    try:
        response = httpx.post(
            "https://discord.com/api/v10/oauth2/token",
            data={
                "client_id": settings.discord_application_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_oauth_redirect_uri,
            },
            timeout=10,
        )
        response.raise_for_status()
        token_result = response.json()
        guild = token_result.get("guild") or {}
        guild_id = str(guild.get("id") or "")
        if not re.fullmatch(r"[0-9]+", guild_id):
            raise ValueError("Discord did not return the installed server")
        options = DiscordClient().guild_options(guild_id)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="Discord installation could not be verified"
        ) from exc
    binding = session.get(
        InstallationGuildBinding, intent.installation_id
    ) or InstallationGuildBinding(
        installation_id=intent.installation_id,
        guild_id=guild_id,
        guild_name=str((options.get("guild") or {}).get("name") or guild_id)[:128],
    )
    binding.guild_id = guild_id
    binding.guild_name = str((options.get("guild") or {}).get("name") or guild_id)[:128]
    binding.authorized = True
    binding.updated_at = now
    intent.used_at = now
    session.add(binding)
    session.commit()
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><title>Frontline Discord</title>"
        "<style>body{font-family:system-ui;background:#151713;color:#eee;padding:3rem}"
        "main{max-width:38rem;margin:auto;padding:2rem;border:1px solid #5865f2;border-radius:16px}</style>"
        "<main><h1>Discord-Server verbunden</h1><p>Du kannst dieses Fenster schließen "
        "und im CRCON auf „Discord-Server erkennen“ klicken.</p></main>"
    )


@app.post("/v1/pairing-options")
def pairing_options(
    payload: PairingDiscoveryRequest,
    session: Session = Depends(session_dependency),
):
    callback = str(payload.crcon_callback_url)
    _check_rate_limit(f"pairing-options:{urlsplit(callback).hostname}")
    _validate_crcon_callback(callback)
    _verify_pending_pairing(payload, callback)
    return _pairing_guild_options(payload, session)


@app.post("/v1/pairings", status_code=status.HTTP_201_CREATED)
def pair_installation(
    payload: PairingRequest, session: Session = Depends(session_dependency)
):
    callback = str(payload.crcon_callback_url)
    _check_rate_limit(f"pairing:{urlsplit(callback).hostname}")
    _validate_crcon_callback(callback)
    options = _pairing_guild_options(payload, session)
    guild_id = str(options["guild"]["id"])
    guild_name = str(options["guild"].get("name") or guild_id)[:128]
    channel = next(
        (item for item in options["channels"] if str(item["id"]) == payload.channel_id),
        None,
    )
    if channel is None:
        raise HTTPException(
            status_code=400,
            detail="The selected channel is not available on the installed Discord server",
        )
    try:
        DiscordClient().validate_channel(payload.channel_id, guild_id)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Discord channel cannot be used by this app"
        ) from exc
    action_capability = derive_capability(payload.pairing_id, "actions")
    try:
        response = _crcon_post(
            callback,
            json={
                "pairing_id": payload.pairing_id,
                "pairing_secret": payload.pairing_secret,
                "crcon_action_capability": action_capability,
                "guild_id": guild_id,
                "guild_name": guild_name,
                "channel_id": payload.channel_id,
                "channel_name": str(channel.get("name") or payload.channel_name)[:128],
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json().get("result", response.json())
        installation_id = str(result["installation_id"])
        event_capability = str(result["event_capability"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="CRCON pairing failed") from exc
    crcon_base_url = callback.rsplit("/api/discord/v1/", 1)[0]
    integration = session.get(Integration, installation_id) or Integration(
        installation_id=installation_id,
        crcon_base_url=crcon_base_url,
        guild_id=guild_id,
        channel_id=payload.channel_id,
        event_capability_digest="",
        action_capability_ciphertext="",
    )
    integration.crcon_base_url = crcon_base_url
    integration.guild_id = guild_id
    integration.channel_id = payload.channel_id
    integration.event_capability_digest = digest(event_capability, "events")
    integration.action_capability_ciphertext = encrypt(action_capability)
    integration.enabled = True
    session.add(integration)
    session.commit()
    return {"installation_id": installation_id, "connected": True}


@app.post("/v1/events", status_code=status.HTTP_202_ACCEPTED)
def receive_event(
    envelope: IncidentEventEnvelope,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(session_dependency),
):
    if not idempotency_key or len(idempotency_key) > 160:
        raise HTTPException(
            status_code=400, detail="A valid Idempotency-Key is required"
        )
    integration = _integration_for_event(session, envelope, authorization)
    _purge_expired_relays(session)
    _check_rate_limit(f"events:{integration.installation_id}")
    existing = session.get(EventReceipt, idempotency_key)
    if existing:
        return {"accepted": True, "cached": True}
    mapping = session.execute(
        select(IncidentMessage).where(
            IncidentMessage.installation_id == envelope.installation_id,
            IncidentMessage.incident_id == envelope.incident_id,
        )
    ).scalar_one_or_none()
    if mapping and envelope.incident_revision < mapping.last_revision:
        session.add(
            EventReceipt(
                idempotency_key=idempotency_key,
                installation_id=envelope.installation_id,
                event_id=envelope.event_id,
                event_type=envelope.event_type,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        return {"accepted": True, "cached": True, "stale": True}
    analysis = envelope.analysis
    unavailable = False
    ai_config = envelope.incident.get("ai_config") or {}
    raw_source = str(envelope.incident.get("source") or "")
    ai_toggle = {
        "ai_chat": "chat_enabled",
        "ai_player_name": "names_enabled",
    }.get(raw_source)
    source_ai_enabled = bool(ai_toggle and ai_config.get(ai_toggle, False))
    if analysis is None and envelope.event_type == "created" and source_ai_enabled:
        # Analysis is exclusively produced by CRCON jobs using a customer-owned
        # API key or Codex login. The Discord service never falls back to a
        # Frontline-funded model call while delivering an incident.
        unavailable = True
    squad_subject_ids = _confirmed_squad_subject_ids(envelope.incident)
    is_multi_squad_report = (
        str(envelope.incident.get("source") or "") in {"chat", "manual"}
        and len(squad_subject_ids) > 1
    )
    selected_subject_id = (
        mapping.primary_subject_id
        if mapping and mapping.primary_subject_id in squad_subject_ids
        else None
    )
    message_payload = render_message(
        envelope,
        analysis,
        ai_unavailable=unavailable,
        selected_subject_id=selected_subject_id,
    )
    try:
        message_id = DiscordClient().upsert(
            integration.channel_id,
            message_payload,
            mapping.message_id if mapping else None,
        )
        # Ballots only edit the central case. A terminal failure/dry run needs a
        # new admin alert (editing a Discord card does not notify subscribers).
        report_admin_attention = (
            envelope.event_type in {"report_admin_manual", "report_admin_unknown", "report_admin_dry_run"}
        )
        if (report_admin_attention or envelope.event_type in {
            "leadership_vote_cancelled", "leadership_vote_rejected",
            "leadership_vote_unknown", "leadership_vote_dry_run",
        }) and envelope.incident.get("status") not in {"resolved", "dismissed"}:
            roles = [str(r) for r in envelope.incident.get("admin_notification_role_ids", [])
                     if str(r).isdigit()][:100]
            nonce = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
            DiscordClient().upsert(integration.channel_id, {
                "content": (" ".join(f"<@&{role}>" for role in roles)
                    + (" Report-Admin: Manuelle Prüfung erforderlich. / Report admin: manual review required."
                       if report_admin_attention else
                       " Führungsabstimmung beendet: Admin-Bearbeitung erforderlich. / Leadership vote ended: admin review required.")),
                "message_reference": {"message_id": message_id, "fail_if_not_exists": False},
                "allowed_mentions": {"parse": [], "roles": roles, "replied_user": False},
                "nonce": nonce, "enforce_nonce": True,
            })
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 429:
            raise HTTPException(status_code=429, detail="Discord rate limited") from exc
        raise HTTPException(
            status_code=503, detail="Discord delivery unavailable"
        ) from exc
    now = datetime.now(tz=timezone.utc)
    cheat_review = (envelope.incident.get("report_admin") or {}).get("rule") == "cheating"
    if mapping is None:
        mapping = IncidentMessage(
            installation_id=envelope.installation_id,
            incident_id=envelope.incident_id,
            message_id=message_id,
            channel_id=integration.channel_id,
            last_revision=envelope.incident_revision,
            analysis_id=str(envelope.incident.get("analysis_id") or "") or None,
            suggested_action=(analysis.suggested_action.value if analysis else None),
            suggested_duration_hours=(
                24 if cheat_review else analysis.suggested_duration_hours if analysis else None
            ),
            primary_subject_id=(
                None
                if is_multi_squad_report
                else str(
                    (envelope.incident.get("primary_subject") or {}).get("id") or ""
                )
                or None
            ),
            updated_at=now,
        )
        session.add(mapping)
    else:
        mapping.message_id = message_id
        mapping.last_revision = max(mapping.last_revision, envelope.incident_revision)
        if envelope.incident.get("analysis_id"):
            mapping.analysis_id = str(envelope.incident["analysis_id"])
        if analysis:
            mapping.suggested_action = analysis.suggested_action.value
            mapping.suggested_duration_hours = analysis.suggested_duration_hours
        if cheat_review:
            mapping.suggested_duration_hours = 24
        if is_multi_squad_report:
            if mapping.primary_subject_id not in squad_subject_ids:
                mapping.primary_subject_id = None
        else:
            primary_subject_id = str(
                (envelope.incident.get("primary_subject") or {}).get("id") or ""
            )
            mapping.primary_subject_id = primary_subject_id or None
        mapping.updated_at = now
    session.add(
        EventReceipt(
            idempotency_key=idempotency_key,
            installation_id=envelope.installation_id,
            event_id=envelope.event_id,
            event_type=envelope.event_type,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return {"accepted": True, "cached": True}
    return {"accepted": True, "cached": False, "ai_available": not unavailable}


@app.get("/v1/usage/{installation_id}")
def integration_usage(
    installation_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    integration = session.get(Integration, installation_id)
    if integration is None or not matches(
        _bearer(authorization), integration.event_capability_digest, "events"
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    return _usage_summary(session, installation_id)


@app.get("/v1/ai/{installation_id}/status")
def ai_provider_status(
    installation_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _integration_for_capability(session, installation_id, authorization)
    _check_rate_limit(f"ai-status:{installation_id}")
    return codex_account_status(installation_id)


@app.post("/v1/ai/{installation_id}/login")
def ai_provider_login(
    installation_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _integration_for_capability(session, installation_id, authorization)
    _check_rate_limit(f"ai-login:{installation_id}")
    try:
        return start_device_login(installation_id)
    except CodexRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/ai/{installation_id}/logout")
def ai_provider_logout(
    installation_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _integration_for_capability(session, installation_id, authorization)
    _check_rate_limit(f"ai-logout:{installation_id}")
    try:
        codex_logout(installation_id)
    except CodexRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"connected": False, "state": "disconnected"}


@app.post("/v1/analysis-jobs", status_code=status.HTTP_202_ACCEPTED)
def receive_analysis_job(
    job: ModerationAnalysisJobEnvelope,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(session_dependency),
):
    if not idempotency_key or len(idempotency_key) > 160:
        raise HTTPException(
            status_code=400, detail="A valid Idempotency-Key is required"
        )
    integration = session.get(Integration, job.installation_id)
    if (
        integration is None
        or not integration.enabled
        or not matches(
            _bearer(authorization), integration.event_capability_digest, "events"
        )
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    _check_rate_limit(f"analysis:{integration.installation_id}")
    if session.get(EventReceipt, idempotency_key):
        return {"accepted": True, "cached": True}
    local_hard_hit = _has_local_hard_rule(job.policy, job.matched_rule_ids)
    if job.ai_provider == "codex":
        selected_model = (
            job.player_name_model
            if job.source == ModerationSource.PLAYER_NAME
            else job.ai_model
        )
        result = CodexAnalyzer(job.installation_id).analyze(
            text=job.candidate_text,
            source=job.source,
            policy=job.policy,
            model=selected_model,
            player_ids=[job.player_id] if job.player_id else [],
            force_structured_analysis=local_hard_hit,
            matched_rule_ids=job.matched_rule_ids,
        )
    else:
        api_key = job.api_key
        if not api_key:
            raise HTTPException(
                status_code=409, detail="OpenAI API key is not configured"
            )
        analyzer_settings = get_settings().model_copy(
            update={
                "openai_api_key": api_key,
                "ai_model": job.ai_model,
                "player_name_model": job.player_name_model,
            }
        )
        result = ManagedAnalyzer(settings=analyzer_settings).analyze(
            text=job.candidate_text,
            source=job.source,
            policy=job.policy,
            player_ids=[job.player_id] if job.player_id else [],
            force_structured_analysis=local_hard_hit,
            matched_rule_ids=job.matched_rule_ids,
        )
    if result.analysis is None:
        raise HTTPException(status_code=503, detail="AI analysis unavailable")
    supplied_rules = list(
        dict.fromkeys([*result.analysis.rule_ids, *job.matched_rule_ids])
    )[:20]
    analysis = result.analysis.model_copy(
        update={
            "rule_ids": supplied_rules,
            "hard_hit": result.analysis.hard_hit or local_hard_hit,
        }
    )
    analysis_id = str(uuid.uuid4())
    try:
        callback = _crcon_post(
            f"{integration.crcon_base_url}/api/discord/v1/moderation-results",
            headers={
                "Authorization": (
                    f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                )
            },
            json={
                "installation_id": integration.installation_id,
                "analysis_id": analysis_id,
                "job_id": job.job_id,
                "analysis": analysis.model_dump(mode="json"),
                "policy": job.policy.model_dump(mode="json"),
            },
            timeout=10,
        )
        callback.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503, detail="CRCON analysis callback unavailable"
        ) from exc
    session.add(
        EventReceipt(
            idempotency_key=idempotency_key,
            installation_id=job.installation_id,
            event_id=0,
            event_type="analysis_job",
        )
    )
    session.add(
        TechnicalUsageMetric(
            installation_id=job.installation_id,
            kind=job.source.value,
            model=result.analysis.model_version,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            success=True,
        )
    )
    session.commit()
    return {"accepted": True, "cached": False}


@app.post(
    "/v1/player-name-analysis-batches",
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_player_name_analysis_batch(
    batch: PlayerNameAnalysisBatchEnvelope,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(session_dependency),
):
    """Analyze up to 50 changed names with one subscription/API model turn."""

    if not idempotency_key or len(idempotency_key) > 160:
        raise HTTPException(
            status_code=400, detail="A valid Idempotency-Key is required"
        )
    integration = session.get(Integration, batch.installation_id)
    if (
        integration is None
        or not integration.enabled
        or not matches(
            _bearer(authorization), integration.event_capability_digest, "events"
        )
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    _check_rate_limit(f"analysis:{integration.installation_id}")
    if session.get(EventReceipt, idempotency_key):
        return {"accepted": True, "cached": True}

    def job_receipt_key(job_id: str) -> str:
        return f"name-analysis:{batch.installation_id}:{job_id}"

    pending_jobs = [
        job
        for job in batch.jobs
        if session.get(EventReceipt, job_receipt_key(job.job_id)) is None
    ]
    if not pending_jobs:
        session.add(
            EventReceipt(
                idempotency_key=idempotency_key,
                installation_id=batch.installation_id,
                event_id=0,
                event_type="player_name_analysis_batch",
            )
        )
        session.commit()
        return {"accepted": True, "cached": True, "count": len(batch.jobs)}

    first_job = pending_jobs[0]
    items = [
        PlayerNameBatchInput(
            text=job.candidate_text,
            policy=job.policy,
            player_ids=[job.player_id] if job.player_id else [],
            matched_rule_ids=job.matched_rule_ids,
        )
        for job in pending_jobs
    ]
    if first_job.ai_provider == "codex":
        result = CodexAnalyzer(batch.installation_id).analyze_player_names(
            items=items,
            model=first_job.player_name_model,
        )
    else:
        api_key = first_job.api_key
        if not api_key:
            raise HTTPException(
                status_code=409, detail="OpenAI API key is not configured"
            )
        analyzer_settings = get_settings().model_copy(
            update={
                "openai_api_key": api_key,
                "player_name_model": first_job.player_name_model,
            }
        )
        result = ManagedAnalyzer(settings=analyzer_settings).analyze_player_names(items)
    if result.analyses is None or len(result.analyses) != len(pending_jobs):
        raise HTTPException(status_code=503, detail="AI batch analysis unavailable")

    # Count every real model turn even when a later CRCON callback is unavailable.
    session.add(
        TechnicalUsageMetric(
            installation_id=batch.installation_id,
            kind="ai_player_name_batch",
            model=first_job.player_name_model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            success=True,
        )
    )
    session.commit()

    for job, raw_analysis in zip(pending_jobs, result.analyses, strict=True):
        local_hard_hit = _has_local_hard_rule(job.policy, job.matched_rule_ids)
        supplied_rules = list(
            dict.fromkeys([*raw_analysis.rule_ids, *job.matched_rule_ids])
        )[:20]
        analysis = raw_analysis.model_copy(
            update={
                "rule_ids": supplied_rules,
                "hard_hit": raw_analysis.hard_hit or local_hard_hit,
            }
        )
        try:
            callback = _crcon_post(
                f"{integration.crcon_base_url}/api/discord/v1/moderation-results",
                headers={
                    "Authorization": (
                        f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                    )
                },
                json={
                    "installation_id": integration.installation_id,
                    "analysis_id": str(uuid.uuid4()),
                    "job_id": job.job_id,
                    "analysis": analysis.model_dump(mode="json"),
                    "policy": job.policy.model_dump(mode="json"),
                },
                timeout=10,
            )
            callback.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="CRCON analysis callback unavailable"
            ) from exc
        session.add(
            EventReceipt(
                idempotency_key=job_receipt_key(job.job_id),
                installation_id=batch.installation_id,
                event_id=0,
                event_type="player_name_analysis_job",
            )
        )
        session.commit()

    session.add(
        EventReceipt(
            idempotency_key=idempotency_key,
            installation_id=batch.installation_id,
            event_id=0,
            event_type="player_name_analysis_batch",
        )
    )
    session.commit()
    return {"accepted": True, "cached": False, "count": len(batch.jobs)}


@app.post("/v1/test-messages", status_code=status.HTTP_202_ACCEPTED)
def test_message(
    payload: dict,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    installation_id = str(payload.get("installation_id") or "")
    integration = session.get(Integration, installation_id)
    if integration is None or not matches(
        _bearer(authorization), integration.event_capability_digest, "events"
    ):
        raise HTTPException(status_code=404, detail="Unknown installation capability")
    _check_rate_limit(f"test:{integration.installation_id}")
    DiscordClient().upsert(
        integration.channel_id,
        {
            "embeds": [
                {
                    "title": "CRCON-Verbindung erfolgreich",
                    "description": "Der Frontline Discord Report Bot ist verbunden.",
                    "color": 5763719,
                }
            ],
            "allowed_mentions": {"parse": []},
        },
    )
    return {"accepted": True}


def _verify_discord_signature(request_body: bytes, signature: str, timestamp: str):
    public_key = get_settings().discord_public_key
    if not public_key:
        raise HTTPException(status_code=503, detail="Discord public key not configured")
    try:
        if abs(time() - int(timestamp)) > 300:
            raise ValueError("stale timestamp")
        VerifyKey(bytes.fromhex(public_key)).verify(
            timestamp.encode("utf-8") + request_body, bytes.fromhex(signature)
        )
    except (BadSignatureError, ValueError) as exc:
        raise HTTPException(
            status_code=401, detail="Invalid Discord signature"
        ) from exc


@app.post("/v1/discord/interactions")
async def discord_interaction(
    request: Request,
    x_signature_ed25519: str = Header(default=""),
    x_signature_timestamp: str = Header(default=""),
    session: Session = Depends(session_dependency),
):
    body = await request.body()
    _verify_discord_signature(body, x_signature_ed25519, x_signature_timestamp)
    _purge_expired_relays(session)
    payload = await request.json()
    if payload.get("type") == 1:
        return {"type": 1}
    rate_member = payload.get("member") or {}
    rate_user = rate_member.get("user") or {}
    _check_rate_limit(f"interaction:{payload.get('guild_id')}:{rate_user.get('id')}")
    custom_id = str((payload.get("data") or {}).get("custom_id") or "")
    if payload.get("type") == 3 and custom_id.startswith("confirm:"):
        handle = custom_id.split(":", 1)[1]
        relay = session.get(PreparedActionRelay, handle)
        member = payload.get("member") or {}
        user = member.get("user") or {}
        actor_id = str(user.get("id") or "")
        now = datetime.now(tz=timezone.utc)
        expires_at = relay.expires_at if relay else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if (
            relay is None
            or relay.used_at is not None
            or expires_at is None
            or expires_at <= now
            or relay.actor_id != actor_id
        ):
            return {
                "type": 4,
                "data": {
                    "content": "Bestätigung ist ungültig oder abgelaufen.",
                    "flags": 64,
                },
            }
        integration = session.get(Integration, relay.installation_id)
        if integration is None or not integration.enabled:
            return {
                "type": 4,
                "data": {"content": "Integration ist nicht mehr aktiv.", "flags": 64},
            }
        actor = {
            "discord_id": actor_id,
            "display_name": str(
                member.get("nick")
                or user.get("global_name")
                or user.get("username")
                or "Discord moderator"
            ),
            "role_ids": [str(value) for value in member.get("roles") or []],
        }
        try:
            execution_result = _execute_prepared_action(
                integration,
                preparation_id=relay.preparation_id,
                confirmation_token=decrypt(relay.confirmation_ciphertext),
                interaction_id=str(payload.get("id")),
                guild_id=relay.guild_id,
                channel_id=relay.channel_id,
                actor=actor,
            )
        except httpx.HTTPError as exc:
            return {
                "type": 4,
                "data": {
                    "content": _crcon_interaction_error(exc),
                    "flags": 64,
                },
            }
        relay.used_at = now
        session.commit()
        _send_feedback(
            integration,
            interaction_id=str(payload.get("id")),
            guild_id=relay.guild_id,
            channel_id=relay.channel_id,
            incident_id=relay.incident_id,
            analysis_id=relay.analysis_id,
            actor=actor,
            decision=(
                "accepted"
                if relay.actual_action == relay.suggested_action
                else "overridden"
            ),
            actual_action=relay.actual_action,
        )
        return {
            "type": 4,
            "data": {
                "content": _action_execution_message(
                    execution_result, relay.actual_action
                ),
                "flags": 64,
            },
        }

    choice_match = re.fullmatch(r"choose:([0-9a-f-]{36}):(\d+)", custom_id)
    subject_match = re.fullmatch(r"subject:([0-9a-f-]{36}):(\d+)", custom_id)
    template_match = re.fullmatch(
        r"template:([0-9a-f-]{36}):(\d+):([a-z_]+)", custom_id
    )
    modal_match = re.fullmatch(
        r"action-modal:([0-9a-f-]{36}):(\d+):([a-z_]+)", custom_id
    )
    modal_values: dict[str, str | int] = {}
    selected_template_id: str | None = None
    selected_subject_id: str | None = None
    if payload.get("type") == 3 and subject_match:
        operation = "select_subject"
        incident_id, revision = subject_match.groups()
        selected = (payload.get("data") or {}).get("values") or []
        selected_subject_id = str(selected[0]) if selected else ""
        match = bool(re.fullmatch(r"[0-9a-f-]{36}", selected_subject_id))
    elif payload.get("type") == 3 and choice_match:
        operation = "action"
        incident_id, revision = choice_match.groups()
        selected = (payload.get("data") or {}).get("values") or []
        recommended_action = str(selected[0]) if selected else ""
        match = bool(re.fullmatch(r"[a-z_]+", recommended_action))
    elif payload.get("type") == 3 and template_match:
        operation = "action"
        incident_id, revision, recommended_action = template_match.groups()
        selected = (payload.get("data") or {}).get("values") or []
        selected_template_id = str(selected[0]) if selected else ""
        match = selected_template_id == "custom" or bool(
            re.fullmatch(r"[0-9]+", selected_template_id)
        )
    elif payload.get("type") == 5 and modal_match:
        operation = "action"
        incident_id, revision, recommended_action = modal_match.groups()
        rows = (payload.get("data") or {}).get("components") or []
        modal_values = {
            str(component.get("custom_id")): str(component.get("value") or "").strip()
            for row in rows
            for component in row.get("components", [])
        }
        required_text_key = (
            "message"
            if recommended_action in {"message", "message_reporter"}
            else "reason"
        )
        if not modal_values.get(required_text_key):
            return {
                "type": 4,
                "data": {
                    "content": "Ein Text oder Grund ist erforderlich.",
                    "flags": 64,
                },
            }
        if recommended_action == "temp_ban":
            try:
                modal_values["duration_hours"] = int(modal_values["duration_hours"])
            except (KeyError, ValueError):
                return {
                    "type": 4,
                    "data": {"content": "Die Dauer muss eine Zahl sein.", "flags": 64},
                }
        if recommended_action == "blacklist":
            # CRCON's built-in Default blacklist always has ID 0.  Discord
            # moderators should not need to know or type an internal DB ID.
            modal_values["blacklist_id"] = 0
        match = True
    else:
        match = re.fullmatch(
            r"(action|dismiss|trash|manual|finish|logs|cancel_leadership_vote):"
            r"([0-9a-f-]{36}):(\d+)(?::([a-z_]+))?",
            custom_id,
        )
        if match:
            operation, incident_id, revision, recommended_action = match.groups()
    if not match:
        return {"type": 4, "data": {"content": "Unbekannte Interaktion", "flags": 64}}
    guild_id = str(payload.get("guild_id") or "")
    channel_id = str(payload.get("channel_id") or "")
    integration = session.execute(
        select(Integration).where(
            Integration.guild_id == guild_id,
            Integration.channel_id == channel_id,
            Integration.enabled.is_(True),
        )
    ).scalar_one_or_none()
    if integration is None:
        return {
            "type": 4,
            "data": {"content": "Integration nicht gefunden", "flags": 64},
        }
    mapping = session.execute(
        select(IncidentMessage).where(
            IncidentMessage.installation_id == integration.installation_id,
            IncidentMessage.incident_id == incident_id,
        )
    ).scalar_one_or_none()
    member = payload.get("member") or {}
    user = member.get("user") or {}
    actor = {
        "discord_id": str(user.get("id") or ""),
        "display_name": str(
            member.get("nick")
            or user.get("global_name")
            or user.get("username")
            or "Discord moderator"
        ),
        "role_ids": [str(value) for value in member.get("roles") or []],
    }
    message = payload.get("message") or {}
    has_subject_selector = any(
        str(component.get("custom_id") or "").startswith(f"subject:{incident_id}:")
        for row in message.get("components") or []
        for component in row.get("components") or []
    )
    if operation == "select_subject":
        if mapping is None or not selected_subject_id:
            return {
                "type": 4,
                "data": {"content": "Report-Zuordnung nicht gefunden.", "flags": 64},
            }
        selected_option = next(
            (
                option
                for row in message.get("components") or []
                for component in row.get("components") or []
                if str(component.get("custom_id") or "") == custom_id
                for option in component.get("options") or []
                if str(option.get("value") or "") == selected_subject_id
            ),
            None,
        )
        if not selected_option:
            return {
                "type": 4,
                "data": {
                    "content": "Dieses Ziel ist nicht mehr auswählbar.",
                    "flags": 64,
                },
            }
        try:
            selection_response = _crcon_post(
                f"{integration.crcon_base_url}/api/discord/v1/incidents/select-subject",
                headers={
                    "Authorization": (
                        f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                    )
                },
                json={
                    "interaction_id": str(payload.get("id")),
                    "installation_id": integration.installation_id,
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "incident_id": incident_id,
                    "incident_revision": int(revision),
                    "actor": actor,
                    "operation": "select_subject",
                    "payload": {"subject_id": selected_subject_id},
                },
                timeout=10,
            )
            selection_response.raise_for_status()
            selection_result = selection_response.json().get(
                "result", selection_response.json()
            )
            display_name = str(
                selection_result.get("display_name")
                or selected_option.get("label")
                or "-"
            )
            updated_message = _message_selection_update(
                message,
                subject_id=selected_subject_id,
                display_name=display_name,
            )
        except httpx.HTTPError as exc:
            return {
                "type": 4,
                "data": {"content": _crcon_interaction_error(exc), "flags": 64},
            }
        except (KeyError, TypeError, ValueError):
            return {
                "type": 4,
                "data": {"content": "Die Zielauswahl ist ungültig.", "flags": 64},
            }
        mapping.primary_subject_id = selected_subject_id
        mapping.updated_at = datetime.now(tz=timezone.utc)
        session.commit()
        return {"type": 7, "data": updated_message}
    if (
        operation in {"action", "logs"}
        and recommended_action != "message_reporter"
        and has_subject_selector
        and (mapping is None or not mapping.primary_subject_id)
    ):
        return {
            "type": 4,
            "data": {
                "content": "Bitte wähle zuerst das Squad aus, für das die Aktion gelten soll.",
                "flags": 64,
            },
        }
    if operation == "action" and custom_id.startswith("action:"):
        try:
            claimed = _claim_from_first_button(
                integration,
                interaction_id=str(payload.get("id")),
                guild_id=guild_id,
                channel_id=channel_id,
                incident_id=incident_id,
                revision=int(revision),
                actor=actor,
                payload={"via": "first_button", "button": recommended_action},
            )
            revision = str(claimed["revision"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, httpx.HTTPError):
                message = _crcon_interaction_error(exc)
            else:
                message = "CRCON hat die Übernahme nicht bestätigt."
            return {"type": 4, "data": {"content": message, "flags": 64}}
    if operation == "action" and payload.get("type") != 5:
        # Prefill only; the admin must enter a reason and submit the action.
        # No model/report-assessment result ever executes a cheat ban.
        duration_hours = 24 if mapping and mapping.suggested_duration_hours == 24 else 2
        if selected_template_id == "custom":
            return _action_modal(incident_id, revision, recommended_action, duration_hours=duration_hours)
        crcon_action = (
            "message"
            if recommended_action == "message_reporter"
            else recommended_action
        )
        template_request = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "actor": actor,
            "action": crcon_action,
            **(
                {"template_id": int(selected_template_id)}
                if selected_template_id
                else {}
            ),
        }
        try:
            template_response = _crcon_post(
                f"{integration.crcon_base_url}/api/discord/v1/action-templates",
                headers={
                    "Authorization": (
                        f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                    )
                },
                json=template_request,
                timeout=10,
            )
            template_response.raise_for_status()
            template_result = template_response.json().get(
                "result", template_response.json()
            )
        except httpx.HTTPError as exc:
            return {
                "type": 4,
                "data": {"content": _crcon_interaction_error(exc), "flags": 64},
            }
        if selected_template_id:
            selected_template = template_result.get("selected") or {}
            return _action_modal(
                incident_id,
                revision,
                recommended_action,
                initial_text=str(selected_template.get("content") or ""),
                duration_hours=duration_hours,
            )
        templates = template_result.get("templates") or []
        if templates:
            return _template_picker(
                incident_id, revision, recommended_action, templates
            )
        return _action_modal(incident_id, revision, recommended_action, duration_hours=duration_hours)
    if operation == "logs":
        try:
            claimed = _claim_from_first_button(
                integration,
                interaction_id=str(payload.get("id")),
                guild_id=guild_id,
                channel_id=channel_id,
                incident_id=incident_id,
                revision=int(revision),
                actor=actor,
                payload={"via": "first_button", "button": "logs"},
            )
            log_response = _crcon_post(
                f"{integration.crcon_base_url}/api/discord/v1/incidents/logs",
                headers={
                    "Authorization": (
                        f"Bearer {decrypt(integration.action_capability_ciphertext)}"
                    )
                },
                json={
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "incident_id": incident_id,
                    "actor": actor,
                    **(
                        {"subject_id": mapping.primary_subject_id}
                        if mapping and mapping.primary_subject_id
                        else {}
                    ),
                },
                timeout=10,
            )
            log_response.raise_for_status()
            log_result = log_response.json().get("result", log_response.json())
            lines = log_result.get("lines") or []
            content = "\n".join(str(value) for value in lines) or "Keine Logs gefunden."
            return {
                "type": 4,
                "data": {
                    "content": f"📄 Logs für **{log_result.get('player_name') or 'Spieler'}**\n```\n{content[:1750]}\n```",
                    "flags": 64,
                },
            }
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            message = (
                _crcon_interaction_error(exc)
                if isinstance(exc, httpx.HTTPError)
                else "Die Logs konnten nicht geladen werden."
            )
            return {"type": 4, "data": {"content": message, "flags": 64}}
    endpoint = "actions/prepare" if operation == "action" else "incidents/transition"
    outgoing_operation = {
        "action": "prepare_action",
        "finish": "resolve",
        "trash": "dismiss",
        "manual": "claim",
    }.get(operation, operation)
    actual_action = (
        "message" if recommended_action == "message_reporter" else recommended_action
    )
    transition_payload = {}
    if operation == "manual":
        transition_payload = {"mode": "manual", "via": "first_button"}
    elif operation == "trash":
        transition_payload = {"reason": "wrong_player", "notify_reporter": False}
    elif operation == "dismiss":
        transition_payload = {"reason": "unjustified", "notify_reporter": True}
    data = {
        "interaction_id": str(payload.get("id")),
        "installation_id": integration.installation_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "incident_id": incident_id,
        "incident_revision": int(revision),
        "actor": actor,
        "operation": outgoing_operation,
        "payload": (
            {
                "action": actual_action,
                **modal_values,
                "discord_actor": actor,
                "ai_suggested_action": (mapping.suggested_action if mapping else None),
                "ai_decision": (
                    "accepted"
                    if mapping and mapping.suggested_action == actual_action
                    else "overridden"
                ),
                **(
                    {"reporter_action": True}
                    if recommended_action == "message_reporter"
                    else {}
                ),
                **(
                    {
                        "subject_id": mapping.primary_subject_id,
                    }
                    if mapping
                    and mapping.primary_subject_id
                    and recommended_action != "message_reporter"
                    else {}
                ),
            }
            if recommended_action
            else transition_payload
        ),
    }
    try:
        response = _crcon_post(
            f"{integration.crcon_base_url}/api/discord/v1/{endpoint}",
            headers={
                "Authorization": f"Bearer {decrypt(integration.action_capability_ciphertext)}"
            },
            json=data,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json().get("result", response.json())
    except httpx.HTTPError as exc:
        return {
            "type": 4,
            "data": {"content": _crcon_interaction_error(exc), "flags": 64},
        }
    if operation == "action":
        preview = str(result.get("preview") or actual_action)[:2000]
        if not result.get("requires_second_confirmation"):
            try:
                execution_result = _execute_prepared_action(
                    integration,
                    preparation_id=str(result["preparation_id"]),
                    confirmation_token=str(result["confirmation_token"]),
                    interaction_id=str(payload.get("id")),
                    guild_id=guild_id,
                    channel_id=channel_id,
                    actor=actor,
                )
            except httpx.HTTPError as exc:
                return {
                    "type": 4,
                    "data": {
                        "content": _crcon_interaction_error(exc),
                        "flags": 64,
                    },
                }
            _send_feedback(
                integration,
                interaction_id=str(payload.get("id")),
                guild_id=guild_id,
                channel_id=channel_id,
                incident_id=incident_id,
                analysis_id=mapping.analysis_id if mapping else None,
                actor=actor,
                decision=(
                    "accepted"
                    if mapping and mapping.suggested_action == actual_action
                    else "overridden"
                ),
                actual_action=str(actual_action),
            )
            return {
                "type": 4,
                "data": {
                    "content": (
                        _action_execution_message(execution_result, str(actual_action))
                    ),
                    "flags": 64,
                },
            }
        relay = PreparedActionRelay(
            handle=str(uuid.uuid4()),
            installation_id=integration.installation_id,
            incident_id=incident_id,
            preparation_id=str(result["preparation_id"]),
            confirmation_ciphertext=encrypt(str(result["confirmation_token"])),
            actor_id=actor["discord_id"],
            guild_id=guild_id,
            channel_id=channel_id,
            analysis_id=mapping.analysis_id if mapping else None,
            suggested_action=mapping.suggested_action if mapping else None,
            actual_action=str(actual_action),
            expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
        )
        session.add(relay)
        session.commit()
        content = f"Vorschau: {preview}"
        return {
            "type": 4,
            "data": {
                "content": content[:1800],
                "flags": 64,
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 4,
                                "label": "Endgültig ausführen",
                                "custom_id": f"confirm:{relay.handle}",
                            }
                        ],
                    }
                ],
            },
        }
    else:
        content = {
            "manual": "Du bearbeitest diesen Report jetzt manuell.",
            "finish": "Die manuelle Bearbeitung wurde abgeschlossen.",
            "dismiss": "Der Report wurde als unberechtigt abgelehnt.",
            "trash": "Der Report wurde als Fehlmeldung geschlossen.",
        }.get(operation, f"Incident aktualisiert: {operation}.")
        if operation in {"dismiss", "trash"}:
            mapping = session.execute(
                select(IncidentMessage).where(
                    IncidentMessage.installation_id == integration.installation_id,
                    IncidentMessage.incident_id == incident_id,
                )
            ).scalar_one_or_none()
            _send_feedback(
                integration,
                interaction_id=str(payload.get("id")),
                guild_id=guild_id,
                channel_id=channel_id,
                incident_id=incident_id,
                analysis_id=mapping.analysis_id if mapping else None,
                actor=actor,
                decision="rejected",
                actual_action="none",
            )
    return {"type": 4, "data": {"content": content[:1900], "flags": 64}}
