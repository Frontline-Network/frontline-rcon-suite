"""Authenticated, aggregate-only population analytics API."""

import json
from functools import wraps

from django.views.decorators.csrf import csrf_exempt
from sqlalchemy.exc import SQLAlchemyError

from rcon import population
from rcon.utils import get_server_number

from .auth import api_response, login_required
from .decorators import permission_required, require_http_methods

VIEW = "api.can_view_population_history"
MANAGE = "api.can_mark_seeding_sessions"
CROSS_SERVER = "api.can_view_other_crcon_servers"


def endpoint(permission, methods):
    def decorate(func):
        @csrf_exempt
        @login_required()
        @permission_required(permission, raise_exception=True)
        @require_http_methods(methods)
        @wraps(func)
        def wrapped(request):
            if not request.user.is_active:
                return api_response(
                    failed=True, error="Inactive account", status_code=403
                )
            try:
                result = func(request)
            except PermissionError:
                return api_response(
                    failed=True, error="Server access denied", status_code=403
                )
            except (ValueError, TypeError, KeyError) as error:
                return api_response(failed=True, error=str(error), status_code=400)
            except SQLAlchemyError:
                return api_response(
                    failed=True, error="Population storage unavailable", status_code=503
                )
            response = api_response(result=result, command=func.__name__, failed=False)
            response["Cache-Control"] = "private, no-store"
            return response

        return wrapped

    return decorate


def server_filter(request):
    local = int(get_server_number())
    server = int(request.GET.get("server", local))
    if not 1 <= server <= 2147483647:
        raise ValueError("server must be a positive server number")
    if server != local and not request.user.has_perm(CROSS_SERVER):
        raise PermissionError
    return server


@endpoint(VIEW, ["GET"])
def get_player_count_history(request):
    """GET from/to (UTC ISO or Unix seconds), server, resolution, limit; [from,to).

    Resolution: raw, 1m, 5m, 15m, 60m. Maximum 31 days and 5000 points.
    Raw pagination uses next_from as the inclusive start of the next page.
    Missing buckets contain null counts. Sampling coverage describes recorded
    slots, not continuous observation or a proven causal seeding benefit.
    """
    return population.history(
        server_filter(request),
        request.GET["from"],
        request.GET["to"],
        request.GET.get("resolution", "5m"),
        int(request.GET.get("limit", 5000)),
    )


@endpoint(VIEW, ["GET"])
def get_seeding_sessions(request):
    """GET from/to, optional server; return overlapping manually marked attempts."""
    return population.seeding_history(
        server_filter(request),
        request.GET["from"],
        request.GET["to"],
    )


@endpoint(MANAGE, ["POST"])
def mark_seeding_session(request):
    """POST action=start/end, session_id=UUID, optional starting seeder_count.

    Mutates only the current server; repeating the same UUID/action is safe.
    """
    if request.GET:
        raise ValueError("Seeding markers are server-local and accept a JSON body only")
    data = json.loads(request.body)
    if not isinstance(data, dict) or set(data) - {
        "action",
        "session_id",
        "seeder_count",
    }:
        raise ValueError("Expected action, session_id and optional seeder_count")
    return population.mark_seeding(
        int(get_server_number()),
        data["action"],
        data["session_id"],
        request.user.username,
        data.get("seeder_count"),
    )
