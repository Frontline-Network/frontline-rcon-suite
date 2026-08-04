from datetime import datetime

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from rcon.admin_incidents import (
    IncidentConflict,
    IncidentNotFound,
    InvalidIncidentTransition,
    complete_incident_action,
    create_incident,
    get_incident,
    list_incidents,
    mutate_incident,
    reserve_incident_action,
)
from rcon.utils import get_server_number

from . import views
from .auth import api_response, login_required
from .decorators import require_http_methods
from .mobile import _error, _json_body, _require_enabled
from .mobile_audit import record_mobile_audit
from .multi_servers import forward_mobile_request_to_server

ACTION_PERMISSIONS = {
    "message": "api.can_message_players",
    "punish": "api.can_punish_players",
    "kick": "api.can_kick_players",
    "temp_ban": "api.can_temp_ban_players",
    "comment": "api.can_add_player_comments",
}


def _parse_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _parse_datetime(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@csrf_exempt
@login_required()
@require_http_methods(["GET", "POST"])
def incidents(request):
    command = "mobile_incidents"
    if disabled := _require_enabled(command):
        return disabled
    if request.method == "GET":
        if not request.user.has_perm("api.can_view_admin_incidents"):
            return _error(command, "Missing incident view permission", 403)
        try:
            result = list_incidents(
                statuses=_parse_csv(request.GET.get("status")),
                server_numbers=[
                    int(value) for value in _parse_csv(request.GET.get("server_number"))
                ],
                assigned_to=request.GET.get("assigned_to"),
                updated_after=_parse_datetime(request.GET.get("updated_after")),
                limit=int(request.GET.get("limit", 100)),
            )
        except (TypeError, ValueError) as exc:
            return _error(command, str(exc), 400)
        return api_response(command=command, failed=False, result=result)

    if not request.user.has_perm("api.can_create_admin_incidents"):
        return _error(command, "Missing incident create permission", 403)
    try:
        data = _json_body(request)
        result, created = create_incident(
            server_number=int(data.get("server_number", get_server_number())),
            source="manual",
            reason=str(data["reason"]),
            actor=request.user.username,
            reporter_id=data.get("reporter_id"),
            reporter_name=data.get("reporter_name"),
            target_id=data.get("target_id"),
            target_name=data.get("target_name"),
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    record_mobile_audit(
        username=request.user.username,
        command="mobile_incident_created",
        request=request,
        server_number=result["server_number"],
        incident_id=result["id"],
        arguments={"source": "manual"},
        result={"created": created, "revision": result["revision"]},
    )
    return api_response(
        command=command, failed=False, result={**result, "created": created}
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET", "PATCH"])
def incident_detail(request, incident_id):
    command = "mobile_incident_detail"
    if disabled := _require_enabled(command):
        return disabled
    if not request.user.has_perm("api.can_view_admin_incidents"):
        return _error(command, "Missing incident view permission", 403)
    if request.method == "GET":
        try:
            result = get_incident(str(incident_id))
        except IncidentNotFound as exc:
            return _error(command, str(exc), 404)
        return api_response(command=command, failed=False, result=result)

    try:
        data = _json_body(request)
        operation = str(data["operation"])
        if operation in {"claim", "unclaim"} and not request.user.has_perm(
            "api.can_claim_admin_incidents"
        ):
            return _error(command, "Missing incident claim permission", 403)
        if operation in {
            "resolved",
            "dismissed",
            "reopen",
        } and not request.user.has_perm("api.can_resolve_admin_incidents"):
            return _error(command, "Missing incident resolve permission", 403)
        if operation == "reassign" and not request.user.has_perm(
            "api.can_reassign_admin_incidents"
        ):
            return _error(command, "Missing incident reassign permission", 403)
        if operation == "reassign":
            assigned_to = str(data.get("assigned_to") or "").strip()
            try:
                assignee = User.objects.get(username=assigned_to, is_active=True)
            except User.DoesNotExist:
                return _error(command, "Assignee is not an active CRCON user", 400)
            if not assignee.has_perm("api.can_claim_admin_incidents"):
                return _error(command, "Assignee cannot claim incidents", 400)
        if operation == "link_target" and not request.user.has_perm(
            "api.can_create_admin_incidents"
        ):
            return _error(command, "Missing incident update permission", 403)
        result = mutate_incident(
            str(incident_id),
            actor=request.user.username,
            expected_revision=int(data["revision"]),
            operation=operation,
            payload=data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except (InvalidIncidentTransition, KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    record_mobile_audit(
        username=request.user.username,
        command=f"mobile_incident_{operation}",
        request=request,
        server_number=result["server_number"],
        incident_id=str(incident_id),
        arguments={"expected_revision": data["revision"]},
        result={"status": result["status"], "revision": result["revision"]},
    )
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def incident_notes(request, incident_id):
    command = "mobile_incident_note"
    if disabled := _require_enabled(command):
        return disabled
    if not request.user.has_perm("api.can_create_admin_incidents"):
        return _error(command, "Missing incident create permission", 403)
    try:
        data = _json_body(request)
        result = mutate_incident(
            str(incident_id),
            actor=request.user.username,
            expected_revision=int(data["revision"]),
            operation="note",
            payload=data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except IncidentConflict as exc:
        return _error(command, str(exc), 409)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    record_mobile_audit(
        username=request.user.username,
        command="mobile_incident_note_added",
        request=request,
        server_number=result["server_number"],
        incident_id=str(incident_id),
        arguments={"expected_revision": data["revision"]},
        result={"revision": result["revision"]},
    )
    return api_response(command=command, failed=False, result=result)


def _execute_action(action: str, data: dict, user_name: str, incident: dict):
    player_id = str(data.get("player_id") or incident.get("target_id") or "").strip()
    player_name = str(
        data.get("player_name") or incident.get("target_name") or ""
    ).strip()
    if not player_id:
        raise ValueError("The incident must be linked to a player")
    if action == "message":
        message = str(data.get("message") or "").strip()
        if not message:
            raise ValueError("Message is required")
        return views.rcon_api.message_player(
            player_id,
            message=message,
            by=user_name,
            save_message=True,
            player_name=player_name or None,
        )
    if action in {"punish", "kick", "temp_ban"}:
        reason = str(data.get("reason") or "").strip()
        if not reason:
            raise ValueError("A reason is required")
        if action == "punish":
            return views.rcon_api.punish(
                player_id, reason=reason, by=user_name, player_name=player_name or None
            )
        if action == "kick":
            if data.get("confirmed") is not True:
                raise ValueError("Kick requires explicit confirmation")
            return views.rcon_api.kick(
                player_id, reason=reason, by=user_name, player_name=player_name or None
            )
        duration_hours = int(data.get("duration_hours", 2))
        if data.get("confirmed") is not True or not 1 <= duration_hours <= 720:
            raise ValueError("Temp ban requires confirmation and 1-720 hours")
        return views.rcon_api.temp_ban(
            player_id,
            duration_hours=duration_hours,
            reason=reason,
            by=user_name,
            player_name=player_name or None,
        )
    if action == "comment":
        comment = str(data.get("comment") or "").strip()
        if not comment:
            raise ValueError("Comment is required")
        return views.rcon_api.post_player_comment(
            player_id=player_id, comment=comment, by=user_name
        )
    raise ValueError("Unsupported mobile action")


@csrf_exempt
@login_required()
@require_http_methods(["POST"])
def incident_actions(request, incident_id):
    command = "mobile_incident_action"
    if disabled := _require_enabled(command):
        return disabled
    try:
        data = _json_body(request)
        incident = get_incident(str(incident_id))
        action = str(data["action"])
        permission = ACTION_PERMISSIONS[action]
        server_number = int(data.get("server_number", incident["server_number"]))
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    if not request.user.has_perm(permission):
        return _error(command, "Missing player action permission", 403)
    if server_number != int(incident["server_number"]):
        return _error(command, "Action server does not match the incident", 400)

    if server_number != int(get_server_number()) and not data.get("forwarded"):
        try:
            response = forward_mobile_request_to_server(
                request, server_number, request.path, data
            )
        except ValueError as exc:
            return _error(command, str(exc), 503)
        return HttpResponse(
            content=response.content,
            status=response.status_code,
            content_type=response.headers.get("content-type", "application/json"),
        )

    idempotency_key = request.headers.get("Idempotency-Key", "")
    try:
        reservation, created = reserve_incident_action(
            str(incident_id),
            actor=request.user.username,
            action=action,
            arguments=data,
            idempotency_key=idempotency_key,
        )
    except IncidentNotFound as exc:
        return _error(command, str(exc), 404)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    if not created:
        if reservation["event_type"] == "action_started":
            return _error(command, "Action with this key is still running", 409)
        return api_response(
            command=command,
            failed=reservation["event_type"] == "action_failed",
            result={"cached": True, "event": reservation},
        )

    try:
        result = _execute_action(action, data, request.user.username, incident)
        updated_incident = complete_incident_action(
            idempotency_key, result=result, error=None
        )
        record_mobile_audit(
            username=request.user.username,
            command=f"mobile_player_{action}",
            request=request,
            server_number=server_number,
            incident_id=str(incident_id),
            arguments=data,
            result=result,
        )
    except Exception as exc:
        complete_incident_action(idempotency_key, error=repr(exc))
        record_mobile_audit(
            username=request.user.username,
            command=f"mobile_player_{action}_failed",
            request=request,
            server_number=server_number,
            incident_id=str(incident_id),
            arguments=data,
            result={"error": repr(exc)},
        )
        return _error(command, repr(exc), 502)
    return api_response(
        command=command,
        failed=False,
        result={"action_result": result, "incident": updated_incident},
    )
