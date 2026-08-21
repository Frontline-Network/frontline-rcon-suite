import json
import os
import time
from http.client import CannotSendRequest
from logging import getLogger
from xmlrpc.client import Fault, ServerProxy

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from rcon.api_commands import get_rcon_api
from rcon.discord import send_to_discord_audit
from rcon.cache_utils import get_redis_client
from rcon.support_diagnostics import build_support_diagnostics, preview_support_diagnostics
from rcon.operational_health import rcon_latency_tracker
from rcon.supervisor_runtime import (
    DEFAULT_SERVICES,
    RUNNING,
    STATE_KEY,
    STOPPED,
    decode_service_state,
)
from rcon.system_usage import system_usage_sampler
from rcon.utils import get_server_number
from rconweb.settings import TAG_VERSION

from .audit_log import record_audit
from .auth import api_response, login_required
from .decorators import permission_required, require_content_type, require_http_methods
from .utils import _get_data

logger = getLogger(__name__)

supervisor_client = None
SHARED_SERVICE_NAMES = {service.name for service in DEFAULT_SERVICES}


def _expand_shared_runtime(processes):
    """Expose shared threads through the existing service-management API."""
    runtime = next((p for p in processes if p["name"] == "frontline_runtime"), None)
    if runtime is None:
        return processes

    try:
        state = decode_service_state(get_redis_client().hgetall(STATE_KEY))
    except Exception:
        logger.exception("Unable to read shared supervisor service state")
        state = {}

    now = int(time.time())
    expanded = [p for p in processes if p["name"] != "frontline_runtime"]
    for service_name in sorted(SHARED_SERVICE_NAMES):
        statename = state.get(f"{service_name}:state")
        if statename not in {RUNNING, STOPPED}:
            statename = RUNNING if runtime["statename"] == RUNNING else STOPPED
        process = dict(runtime)
        process.update(
            {
                "name": service_name,
                "group": service_name,
                "description": "Shared Frontline runtime service",
                "statename": statename,
                "state": 20 if statename == RUNNING else 0,
                "start": int(state.get(f"{service_name}:start") or runtime["start"]),
                "stop": int(state.get(f"{service_name}:stop") or runtime["stop"]),
                "now": now,
                "spawnerr": state.get(f"{service_name}:spawnerr", ""),
                "pid": runtime["pid"] if statename == RUNNING else 0,
            }
        )
        expanded.append(process)
    return expanded


def _uses_shared_runtime(client) -> bool:
    return any(
        process["name"] == "frontline_runtime"
        for process in client.supervisor.getAllProcessInfo()
    )


def _set_shared_service_state(service_name: str, action: str, now: int | None = None):
    state = RUNNING if action == "START" else STOPPED
    timestamp = int(time.time()) if now is None else now
    get_redis_client().hset(
        STATE_KEY,
        mapping={
            f"{service_name}:desired": state,
            f"{service_name}:state": state,
            f"{service_name}:{'start' if state == RUNNING else 'stop'}": timestamp,
        },
    )
    return True


def get_supervisor_client():
    global supervisor_client

    if not supervisor_client:
        url = os.getenv("SUPERVISOR_RPC_URL")
        if not url:
            raise ValueError("Can't start services, the url of supervisor isn't set")
        supervisor_client = ServerProxy(url)

    return supervisor_client


def _support_diagnostics_package():
    """Assemble only allowlisted aggregate values for a support export."""

    client = get_supervisor_client()
    processes = _expand_shared_runtime(client.supervisor.getAllProcessInfo())
    try:
        game = get_rcon_api().config.game.value
    except Exception:
        logger.warning("Unable to determine the game profile for support diagnostics")
        game = None

    return build_support_diagnostics(
        version=TAG_VERSION,
        game=game,
        server_number=int(get_server_number()),
        system_usage=system_usage_sampler.get_snapshot(),
        services=processes,
        known_service_names=SHARED_SERVICE_NAMES | {
            "frontline_runtime",
            "log_stream",
            "campaign_messages",
            "auto_settings",
            "automod",
            "cron",
            "expiring_vips",
            "live_stats_refresh",
            "autobalancer",
            "blacklists",
            "log_recorder",
            "routines",
        },
    )


def _operational_health(window_minutes: int) -> dict:
    """Return bounded component health without a new RCON probe."""

    system = system_usage_sampler.get_snapshot(window_seconds=window_minutes * 60)
    try:
        redis_state = "healthy" if get_redis_client().ping() else "degraded"
    except Exception:
        redis_state = "offline"
    try:
        processes = _expand_shared_runtime(
            get_supervisor_client().supervisor.getAllProcessInfo()
        )
        service_states = [process.get("statename") for process in processes]
        services = {
            "state": (
                "degraded"
                if any(state in {"FATAL", "EXITED"} for state in service_states)
                else "healthy"
            ),
            "running": sum(state == RUNNING for state in service_states),
            "failed": sum(state in {"FATAL", "EXITED"} for state in service_states),
        }
    except Exception:
        services = {"state": "unknown", "running": None, "failed": None}
    try:
        from .discord_integration import _delivery_summary

        outbox = _delivery_summary()
    except Exception:
        outbox = {"state": "unknown", "pending_count": None}
    return {
        "schema_version": 1,
        "generated_at": system["generated_at"],
        "window_minutes": window_minutes,
        "overall_state": (
            "critical"
            if system["status"] == "critical" or redis_state == "offline"
            else "degraded"
            if system["status"] in {"warning", "partial"}
            or services["state"] == "degraded"
            or outbox.get("state") in {"pending", "retrying"}
            else "healthy"
        ),
        "components": {
            "process": {"state": system["status"], "last_checked_at": system["sampled_at"]},
            "redis": {"state": redis_state, "last_checked_at": system["generated_at"]},
            "services": services,
            "rcon": rcon_latency_tracker.snapshot(window_seconds=window_minutes * 60),
            "discord_outbox": outbox,
        },
        "system_usage": system,
    }


@csrf_exempt
@login_required()
@permission_required("api.can_view_available_services", raise_exception=True)
@require_http_methods(["GET"])
def get_operational_health(request):
    try:
        window_minutes = int(request.GET.get("window_minutes", "15"))
    except ValueError:
        window_minutes = 15
    if window_minutes not in {5, 15, 60}:
        return api_response(
            command="get_operational_health",
            failed=True,
            error="window_minutes must be one of 5, 15 or 60",
            status_code=400,
        )
    return api_response(
        result=_operational_health(window_minutes),
        command="get_operational_health",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_available_services", raise_exception=True)
@require_http_methods(["GET"])
def get_support_diagnostics_preview(request):
    package = _support_diagnostics_package()
    return api_response(
        result=preview_support_diagnostics(package),
        command="get_support_diagnostics_preview",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_available_services", raise_exception=True)
@require_http_methods(["GET"])
def download_support_diagnostics(request):
    package = _support_diagnostics_package()
    response = HttpResponse(
        json.dumps(package, separators=(",", ":"), ensure_ascii=False),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = "attachment; filename=frontline-rcon-support-diagnostics.json"
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@login_required()
@permission_required("api.can_view_available_services", raise_exception=True)
@require_http_methods(["GET"])
def get_services(request):
    info = {
        "broadcasts": "The automatic broadcasts.",
        "campaign_messages": "Staggered campaign messages to individual players.",
        "log_event_loop": "Blacklist enforcement, chat/kill forwarding, player history, etc...",
        "log_stream": "Optionally store game server logs in a redis stream",
        "auto_settings": "Applies commands automaticaly based on your rules.",
        "automod": "Applies the configured automatic moderation rules.",
        "cron": "The scheduler, cleans logs and whatever you added.",
        "expiring_vips": "Removes expired VIPs and reconciles active VIPs.",
        "live_stats_refresh": "Updates live player and game statistics.",
        "autobalancer": "Monitors and balances the teams.",
        "blacklists": "Processes shared blacklist updates.",
        "log_recorder": "Persists game-server logs.",
        "routines": "Runs recurring RCON maintenance routines.",
    }
    client = get_supervisor_client()

    try:
        processes = _expand_shared_runtime(client.supervisor.getAllProcessInfo())
        result = [dict(info=info.get(p["name"], ""), **p) for p in processes]
    except:
        if os.getenv("DJANGO_DEBUG"):
            result = []
        else:
            raise
    return api_response(
        result=result,
        command="get_services",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_toggle_services", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
@require_content_type()
def do_service(request):
    data = _get_data(request)
    client = get_supervisor_client()
    error = None
    res = None
    command_name = "do_service"
    failed = False

    actions = {
        "START": client.supervisor.startProcess,
        "STOP": client.supervisor.stopProcess,
    }
    action = data.get("action")
    service_name = data.get("service_name")

    if not action or action.upper() not in actions:
        failed = True
        return api_response(
            command=command_name,
            arguments=data,
            failed=failed,
            error="action must be START or STOP",
            status_code=400,
        )
    if not service_name:
        failed = True
        return api_response(
            command=command_name,
            arguments=data,
            failed=failed,
            error="service_name must be set",
            status_code=400,
        )

    try:
        normalized_action = action.upper()
        if service_name in SHARED_SERVICE_NAMES and _uses_shared_runtime(client):
            res = _set_shared_service_state(service_name, normalized_action)
        else:
            res = actions[normalized_action](service_name)
        send_to_discord_audit(
            message=f"{service_name} {action}",
            command_name=f"service {action}",
            by=request.user.username,
        )
    except CannotSendRequest as e:
        error = "Service request already sent"
        logger.info(f"{error=}")
    except Fault as e:
        error = repr(e)

    return api_response(
        command=command_name,
        arguments=data,
        failed=failed,
        result=res,
        error=error,
    )
