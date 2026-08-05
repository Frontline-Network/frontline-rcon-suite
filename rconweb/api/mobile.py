import json
import os
import secrets
import time
import uuid
from datetime import timedelta
from urllib.parse import urlencode, urlparse

from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rcon.admin_incidents import latest_incident_event_cursor
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.user_config.webhooks import AdminPingWebhooksUserConfig
from rcon.utils import get_server_number
from rconweb.settings import DEBUG, SECRET_KEY, TAG_VERSION

from .auth import api_response, login_required
from .decorators import permission_required, require_http_methods
from .mobile_audit import record_mobile_audit
from .mobile_tokens import (
    InvalidMobileToken,
    issue_device_tokens,
    random_token,
    refresh_device_tokens,
    revoke_mobile_device,
    token_digest,
)
from .models import MobileDevice, MobilePairing
from .multi_servers import mobile_server_list

PAIRING_LIFETIME = timedelta(seconds=120)
RECENT_AUTH_SECONDS = 5 * 60
MOBILE_PROTOCOL_VERSION = 1


def _json_body(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        value = json.loads(request.body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


def _error(command: str, message: str, status: int):
    return api_response(command=command, failed=True, error=message, status_code=status)


def mobile_integration_enabled() -> bool:
    return os.getenv("MOBILE_INTEGRATION_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _incident_retention_days() -> int:
    try:
        return max(1, int(os.getenv("MOBILE_INCIDENT_RETENTION_DAYS", "90")))
    except ValueError:
        return 90


def _mobile_context_fuzzy_threshold() -> float:
    try:
        value = float(os.getenv("MOBILE_CONTEXT_FUZZY_THRESHOLD", "0.74"))
    except (TypeError, ValueError):
        value = 0.74
    return max(0.0, min(value, 1.0))


def _incident_triggers() -> list[str]:
    configured = os.getenv("MOBILE_INCIDENT_TRIGGERS", "").strip()
    if configured:
        return [value.strip() for value in configured.split(",") if value.strip()]
    try:
        inherited = AdminPingWebhooksUserConfig.load_from_db().trigger_words
    except Exception:
        inherited = []
    return [value.strip() for value in inherited if value.strip()] or ["!admin"]


def _require_enabled(command: str):
    if not mobile_integration_enabled():
        return _error(command, "Mobile integration is disabled", 404)
    return None


def _installation_id() -> str:
    configured = os.getenv("MOBILE_INSTALLATION_ID")
    if configured:
        return configured
    database_name = os.getenv("HLL_DB_NAME", "rcon")
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"crcon:{SECRET_KEY}:{database_name}"))


def _public_base_url(request: HttpRequest) -> str:
    value = os.getenv("MOBILE_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not value and DEBUG:
        value = request.build_absolute_uri("/").rstrip("/")
    parsed = urlparse(value)
    allow_http = DEBUG or os.getenv("MOBILE_ALLOW_INSECURE_HTTP") == "1"
    if not parsed.netloc or parsed.scheme not in (
        {"http", "https"} if allow_http else {"https"}
    ):
        raise ValueError("MOBILE_PUBLIC_BASE_URL must be a valid HTTPS URL")
    return value


def _device_dict(device: MobileDevice) -> dict:
    return {
        "id": str(device.id),
        "username": device.user.username,
        "name": device.name,
        "platform": device.platform,
        "app_version": device.app_version,
        "notifications_enabled": device.notifications_enabled,
        "created_at": device.created_at,
        "last_seen_at": device.last_seen_at,
        "revoked_at": device.revoked_at,
        "refresh_expires_at": device.refresh_expires_at,
        "absolute_expires_at": device.absolute_expires_at,
    }


def _pairing_dict(pairing: MobilePairing) -> dict:
    return {
        "id": str(pairing.id),
        "state": pairing.state,
        "verification_code": (
            pairing.verification_code
            if pairing.state
            in {MobilePairing.State.SCANNED, MobilePairing.State.APPROVED}
            else None
        ),
        "device_name": pairing.device_name,
        "platform": pairing.platform,
        "app_version": pairing.app_version,
        "created_at": pairing.created_at,
        "expires_at": pairing.expires_at,
    }


@csrf_exempt
@require_http_methods(["GET"])
def discovery(request):
    command = "mobile_discovery"
    if disabled := _require_enabled(command):
        return disabled
    try:
        base_url = _public_base_url(request)
    except ValueError as exc:
        return _error(command, str(exc), 503)
    try:
        short_name = RconServerSettingsUserConfig.load_from_db().short_name
    except Exception:
        short_name = "CRCON"
    return api_response(
        command=command,
        failed=False,
        result={
            "protocol_version": MOBILE_PROTOCOL_VERSION,
            "minimum_app_version": "0.1.0",
            "installation_id": _installation_id(),
            "display_name": short_name or "CRCON",
            "base_url": base_url,
            "crcon_version": TAG_VERSION,
        },
    )


@csrf_exempt
@login_required()
@permission_required("api.can_manage_own_mobile_devices", raise_exception=True)
@require_http_methods(["POST"])
def create_pairing(request):
    command = "mobile_create_pairing"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
        base_url = _public_base_url(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)

    recent_auth_at = float(request.session.get("mobile_recent_auth_at", 0))
    if time.time() - recent_auth_at > RECENT_AUTH_SECONDS:
        password = data.get("password", "")
        if not password or not request.user.check_password(password):
            return _error(command, "Password confirmation is required", 401)
        request.session["mobile_recent_auth_at"] = time.time()

    MobilePairing.objects.filter(
        user=request.user,
        state__in=(MobilePairing.State.PENDING, MobilePairing.State.SCANNED),
    ).update(state=MobilePairing.State.DENIED)
    raw_secret = random_token("crcon_pair")
    pairing = MobilePairing.objects.create(
        user=request.user,
        secret_digest=token_digest(raw_secret, "pairing"),
        expires_at=timezone.now() + PAIRING_LIFETIME,
    )
    qr_payload = "crcon://pair?" + urlencode(
        {
            "v": MOBILE_PROTOCOL_VERSION,
            "base": base_url,
            "pairing_id": str(pairing.id),
            "secret": raw_secret,
        }
    )
    result = _pairing_dict(pairing)
    result["qr_payload"] = qr_payload
    record_mobile_audit(
        username=request.user.username,
        command="mobile_pairing_created",
        request=request,
        arguments={"pairing_id": str(pairing.id)},
        result={"state": pairing.state, "expires_at": pairing.expires_at},
    )
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@permission_required("api.can_manage_own_mobile_devices", raise_exception=True)
@require_http_methods(["GET"])
def pairing_status(request, pairing_id):
    command = "mobile_pairing_status"
    if disabled := _require_enabled(command):
        return disabled
    try:
        pairing = MobilePairing.objects.get(pk=pairing_id, user=request.user)
    except MobilePairing.DoesNotExist:
        return _error(command, "Pairing not found", 404)
    if pairing.expires_at <= timezone.now() and pairing.state not in {
        MobilePairing.State.CONSUMED,
        MobilePairing.State.DENIED,
    }:
        pairing.state = MobilePairing.State.DENIED
        pairing.save(update_fields=("state",))
    return api_response(command=command, failed=False, result=_pairing_dict(pairing))


@csrf_exempt
@require_http_methods(["POST"])
def scan_pairing(request, pairing_id):
    command = "mobile_scan_pairing"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
        raw_secret = str(data["secret"])
        device_name = str(data["device_name"]).strip()[:128]
        platform = str(data["platform"]).strip().lower()[:32]
    except (KeyError, ValueError) as exc:
        return _error(command, f"Missing or invalid field: {exc}", 400)
    if not device_name or platform not in {"android", "ios"}:
        return _error(command, "A device name and supported platform are required", 400)

    with transaction.atomic():
        try:
            pairing = MobilePairing.objects.select_for_update().get(pk=pairing_id)
        except (MobilePairing.DoesNotExist, ValueError):
            return _error(command, "Pairing not found", 404)
        if pairing.expires_at <= timezone.now():
            pairing.state = MobilePairing.State.DENIED
            pairing.save(update_fields=("state",))
            return _error(command, "Pairing expired", 410)
        if pairing.state != MobilePairing.State.PENDING:
            return _error(command, "Pairing was already scanned", 409)
        if not secrets.compare_digest(
            pairing.secret_digest, token_digest(raw_secret, "pairing")
        ):
            return _error(command, "Invalid pairing secret", 401)

        raw_exchange_token = random_token("crcon_exchange")
        pairing.exchange_token_digest = token_digest(raw_exchange_token, "exchange")
        pairing.verification_code = f"{secrets.randbelow(1_000_000):06d}"
        pairing.device_name = device_name
        pairing.platform = platform
        pairing.app_version = str(data.get("app_version", ""))[:32]
        pairing.push_handle = str(data.get("push_handle", ""))[:255]
        pairing.push_capability = str(data.get("push_capability", ""))[:255]
        pairing.scanned_at = timezone.now()
        pairing.state = MobilePairing.State.SCANNED
        pairing.save()

    record_mobile_audit(
        username=pairing.user.username,
        command="mobile_pairing_scanned",
        arguments={
            "pairing_id": str(pairing.id),
            "device_name": pairing.device_name,
            "platform": pairing.platform,
            "app_version": pairing.app_version,
        },
        result={"state": pairing.state},
    )

    return api_response(
        command=command,
        failed=False,
        result={
            "state": pairing.state,
            "verification_code": pairing.verification_code,
            "exchange_token": raw_exchange_token,
            "expires_at": pairing.expires_at,
        },
    )


@csrf_exempt
@login_required()
@permission_required("api.can_manage_own_mobile_devices", raise_exception=True)
@require_http_methods(["POST"])
def approve_pairing(request, pairing_id):
    command = "mobile_approve_pairing"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)

    with transaction.atomic():
        try:
            pairing = MobilePairing.objects.select_for_update().get(
                pk=pairing_id, user=request.user
            )
        except (MobilePairing.DoesNotExist, ValueError):
            return _error(command, "Pairing not found", 404)
        if pairing.expires_at <= timezone.now():
            pairing.state = MobilePairing.State.DENIED
            pairing.save(update_fields=("state",))
            return _error(command, "Pairing expired", 410)
        if pairing.state != MobilePairing.State.SCANNED:
            return _error(command, "Pairing is not waiting for approval", 409)
        approve = data.get("approve", True)
        if not isinstance(approve, bool):
            return _error(command, "approve must be a boolean", 400)
        if not approve:
            pairing.state = MobilePairing.State.DENIED
            pairing.save(update_fields=("state",))
            record_mobile_audit(
                username=request.user.username,
                command="mobile_pairing_denied",
                request=request,
                arguments={
                    "pairing_id": str(pairing.id),
                    "device_name": pairing.device_name,
                    "platform": pairing.platform,
                },
                result={"state": pairing.state},
            )
            return api_response(
                command=command, failed=False, result={"state": pairing.state}
            )
        if str(data.get("verification_code", "")) != pairing.verification_code:
            return _error(command, "Verification code does not match", 400)
        pairing.state = MobilePairing.State.APPROVED
        pairing.approved_at = timezone.now()
        pairing.save(update_fields=("state", "approved_at"))
    record_mobile_audit(
        username=request.user.username,
        command="mobile_pairing_approved",
        request=request,
        arguments={
            "pairing_id": str(pairing.id),
            "device_name": pairing.device_name,
            "platform": pairing.platform,
        },
        result={"state": pairing.state},
    )
    return api_response(command=command, failed=False, result=_pairing_dict(pairing))


@csrf_exempt
@require_http_methods(["POST"])
def exchange_pairing(request, pairing_id):
    command = "mobile_exchange_pairing"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
        raw_exchange_token = str(data["exchange_token"])
    except (KeyError, ValueError) as exc:
        return _error(command, f"Missing or invalid field: {exc}", 400)

    with transaction.atomic():
        try:
            pairing = (
                MobilePairing.objects.select_for_update()
                .select_related("user")
                .get(
                    pk=pairing_id,
                    exchange_token_digest=token_digest(raw_exchange_token, "exchange"),
                )
            )
        except (MobilePairing.DoesNotExist, ValueError):
            return _error(command, "Invalid exchange token", 401)
        if pairing.expires_at <= timezone.now():
            return _error(command, "Pairing expired", 410)
        if pairing.state == MobilePairing.State.SCANNED:
            return _error(command, "Pairing is awaiting web approval", 202)
        if pairing.state == MobilePairing.State.DENIED:
            return _error(command, "Pairing was denied", 403)
        if pairing.state != MobilePairing.State.APPROVED:
            return _error(command, "Pairing is no longer available", 409)

        device = MobileDevice.objects.create(
            user=pairing.user,
            name=pairing.device_name,
            platform=pairing.platform,
            app_version=pairing.app_version,
            push_handle=pairing.push_handle,
            push_capability=pairing.push_capability,
        )
        tokens = issue_device_tokens(device, initialize_absolute_expiry=True)
        pairing.state = MobilePairing.State.CONSUMED
        pairing.consumed_at = timezone.now()
        pairing.exchange_token_digest = None
        pairing.save(update_fields=("state", "consumed_at", "exchange_token_digest"))
    record_mobile_audit(
        username=device.user.username,
        command="mobile_device_paired",
        device_id=str(device.id),
        arguments={
            "pairing_id": str(pairing.id),
            "device_name": device.name,
            "platform": device.platform,
            "app_version": device.app_version,
        },
        result={"state": pairing.state},
    )
    return api_response(
        command=command,
        failed=False,
        result={
            **tokens,
            "installation_id": _installation_id(),
            "username": device.user.username,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token(request):
    command = "mobile_refresh_token"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
        tokens = refresh_device_tokens(
            str(data["device_id"]), str(data["refresh_token"])
        )
    except (KeyError, ValueError, InvalidMobileToken) as exc:
        return _error(command, str(exc), 401)
    device = MobileDevice.objects.select_related("user").get(pk=tokens["device_id"])
    record_mobile_audit(
        username=device.user.username,
        command="mobile_tokens_refreshed",
        device_id=str(device.id),
        result={"access_expires_at": tokens["access_expires_at"]},
    )
    return api_response(command=command, failed=False, result=tokens)


@csrf_exempt
@login_required()
@permission_required("api.can_manage_own_mobile_devices", raise_exception=True)
@require_http_methods(["GET"])
def devices(request):
    command = "mobile_devices"
    if disabled := _require_enabled(command):
        return disabled
    queryset = MobileDevice.objects.select_related("user")
    if request.GET.get("all") == "true" and request.user.has_perm(
        "api.can_manage_all_mobile_devices"
    ):
        pass
    else:
        queryset = queryset.filter(user=request.user)
    return api_response(
        command=command,
        failed=False,
        result=[_device_dict(device) for device in queryset],
    )


def _device_for_user(request, device_id):
    queryset = MobileDevice.objects.select_related("user")
    if request.user.has_perm("api.can_manage_all_mobile_devices"):
        return queryset.get(pk=device_id)
    return queryset.get(pk=device_id, user=request.user)


@csrf_exempt
@login_required()
@permission_required("api.can_manage_own_mobile_devices", raise_exception=True)
@require_http_methods(["PATCH", "DELETE"])
def device_detail(request, device_id):
    command = "mobile_device_detail"
    if disabled := _require_enabled(command):
        return disabled
    try:
        device = _device_for_user(request, device_id)
    except (MobileDevice.DoesNotExist, ValueError):
        return _error(command, "Device not found", 404)
    authenticated_device = getattr(request, "mobile_device", None)
    if authenticated_device and authenticated_device.pk != device.pk:
        return _error(command, "A mobile device can only update itself", 403)
    if request.method == "DELETE":
        revoke_mobile_device(device)
        record_mobile_audit(
            username=request.user.username,
            command="mobile_device_revoked",
            request=request,
            device_id=str(device.id),
            arguments={"device_name": device.name, "device_user": device.user.username},
            result={"revoked": True},
        )
        return api_response(command=command, failed=False, result={"revoked": True})
    try:
        data = _json_body(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    update_fields = []
    if "name" in data:
        name = str(data["name"]).strip()[:128]
        if not name:
            return _error(command, "Device name cannot be empty", 400)
        device.name = name
        update_fields.append("name")
    if "notifications_enabled" in data:
        if not isinstance(data["notifications_enabled"], bool):
            return _error(command, "notifications_enabled must be a boolean", 400)
        device.notifications_enabled = data["notifications_enabled"]
        update_fields.append("notifications_enabled")
    if "push_handle" in data or "push_capability" in data:
        push_handle = str(data.get("push_handle", ""))[:255]
        push_capability = str(data.get("push_capability", ""))[:255]
        if bool(push_handle) != bool(push_capability):
            return _error(
                command, "Push handle and capability must be updated together", 400
            )
        device.push_handle = push_handle
        device.push_capability = push_capability
        update_fields.extend(("push_handle", "push_capability"))
    if update_fields:
        device.save(update_fields=update_fields)
        record_mobile_audit(
            username=request.user.username,
            command="mobile_device_updated",
            request=request,
            device_id=str(device.id),
            arguments={
                "device_name": device.name,
                "device_user": device.user.username,
                "updated_fields": update_fields,
            },
            result={"updated": True},
        )
    return api_response(command=command, failed=False, result=_device_dict(device))


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def bootstrap(request):
    command = "mobile_bootstrap"
    if disabled := _require_enabled(command):
        return disabled
    permissions = sorted(request.user.get_all_permissions())
    mobile_device = getattr(request, "mobile_device", None)
    # Assignment is deliberately limited to users who can themselves claim a
    # mobile incident.  This keeps the directory useful for handovers without
    # exposing the complete CRCON user list to every mobile device.
    assignable_admins: list[str] = []
    if request.user.has_perm("api.can_reassign_admin_incidents"):
        assignable_admins = [
            user.username
            for user in User.objects.filter(is_active=True).order_by("username")
            if user.has_perm("api.can_claim_admin_incidents")
        ]
    try:
        config = RconServerSettingsUserConfig.load_from_db()
        display_name = config.short_name or "CRCON"
    except Exception:
        display_name = "CRCON"
    return api_response(
        command=command,
        failed=False,
        result={
            "installation_id": _installation_id(),
            "display_name": display_name,
            "server_number": int(get_server_number()),
            "servers": mobile_server_list(request, display_name),
            "crcon_version": TAG_VERSION,
            "protocol_version": MOBILE_PROTOCOL_VERSION,
            "incident_cursor": latest_incident_event_cursor(),
            "mobile_configuration": {
                "enabled": mobile_integration_enabled(),
                "public_base_url": os.getenv("MOBILE_PUBLIC_BASE_URL", ""),
                "incident_triggers": _incident_triggers(),
                "incident_retention_days": _incident_retention_days(),
                "context_v2": os.getenv("MOBILE_CONTEXT_V2", "disabled"),
                "context_fuzzy_threshold": _mobile_context_fuzzy_threshold(),
                "push_relay_configured": bool(
                    os.getenv("MOBILE_PUSH_RELAY_URL", "").strip()
                ),
            },
            "user": {
                "username": request.user.username,
                "is_superuser": request.user.is_superuser,
                "permissions": permissions,
                "assignable_admins": assignable_admins,
            },
            "device": _device_dict(mobile_device) if mobile_device else None,
        },
    )
