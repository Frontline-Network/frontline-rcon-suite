import os
import time
from http.client import CannotSendRequest
from logging import getLogger
from xmlrpc.client import Fault, ServerProxy

from django.views.decorators.csrf import csrf_exempt

from rcon.discord import send_to_discord_audit
from rcon.cache_utils import get_redis_client
from rcon.supervisor_runtime import (
    DEFAULT_SERVICES,
    RUNNING,
    STATE_KEY,
    STOPPED,
    decode_service_state,
)

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


def get_supervisor_client():
    global supervisor_client

    if not supervisor_client:
        url = os.getenv("SUPERVISOR_RPC_URL")
        if not url:
            raise ValueError("Can't start services, the url of supervisor isn't set")
        supervisor_client = ServerProxy(url)

    return supervisor_client


@csrf_exempt
@login_required()
@permission_required("api.can_view_available_services", raise_exception=True)
@require_http_methods(["GET"])
def get_services(request):
    info = {
        "broadcasts": "The automatic broadcasts.",
        "log_event_loop": "Blacklist enforcement, chat/kill forwarding, player history, etc...",
        "log_stream": "Optionally store game server logs in a redis stream",
        "auto_settings": "Applies commands automaticaly based on your rules.",
        "cron": "The scheduler, cleans logs and whatever you added.",
        "expiring_vips": "Removes expired VIPs and reconciles active VIPs.",
        "live_stats": "Updates live player and game statistics.",
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
            now = int(time.time())
            state = RUNNING if normalized_action == "START" else STOPPED
            mapping = {
                f"{service_name}:desired": state,
                f"{service_name}:state": state,
                f"{service_name}:{'start' if state == RUNNING else 'stop'}": now,
            }
            get_redis_client().hset(STATE_KEY, mapping=mapping)
            res = True
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
