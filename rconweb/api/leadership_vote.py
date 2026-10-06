"""Retired leadership voting: historical status/cancellation, no activation."""

import json
from functools import wraps

from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from sqlalchemy import select

from rcon.admin_incidents import IncidentConflict
from rcon.leadership_vote import storage
from rcon.models import LeadershipVote
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from rcon.utils import get_server_number

from .auth import api_response, login_required
from .mobile_audit import record_mobile_audit

MANAGE = "api.can_manage_leadership_votes"
VIEW = "api.can_view_admin_incidents"
CLAIM = "api.can_claim_admin_incidents"
KICK = "api.can_kick_players"


def endpoint(perms, methods):
    def decorate(func):
        @csrf_exempt
        @login_required()
        @wraps(func)
        def wrapped(request, **kwargs):
            if not request.user.is_active or not request.user.has_perms(perms):
                return api_response(
                    failed=True,
                    error="Missing leadership vote permission",
                    status_code=403,
                )
            if request.method not in methods:
                return api_response(
                    failed=True, error="Method not allowed", status_code=405
                )
            try:
                result = func(request, server=int(get_server_number()), **kwargs)
                response = api_response(
                    result=result, failed=False, command="leadership_vote"
                )
                response["Cache-Control"] = "private, no-store"
                return response
            except PermissionError as exc:
                return api_response(failed=True, error=str(exc), status_code=403)
            except IncidentConflict as exc:
                return api_response(failed=True, error=str(exc), status_code=409)
            except LookupError as exc:
                return api_response(failed=True, error=str(exc), status_code=404)
            except (ValueError, TypeError) as exc:
                return api_response(failed=True, error=str(exc), status_code=400)

        return wrapped

    return decorate


def audit(request, command, server, args=None):
    record_mobile_audit(
        username=request.user.username,
        command="leadership_vote_" + command,
        server_number=server,
        arguments=args or {},
    )


@endpoint([MANAGE], {"GET", "PUT"})
def configuration(request, server):
    if request.method == "PUT":
        if request.content_type != "application/json" or len(request.body) > 4096:
            raise ValueError("Small JSON configuration required")
        cfg = Config.model_validate(json.loads(request.body))
        if cfg.enabled:
            raise ValueError("Leadership voting has been retired; configure Report Admin instead")
        storage.configure(server, cfg, request.user.username)
        audit(request, "configure", server, cfg.model_dump())
    with storage.enter_session() as sess:
        result = {**storage.config(sess, server).model_dump(), "enabled": False}
    audit(request, "config_read", server)
    return {
        "config": result,
        "can_enable": False,
        "conflicts": [],
        "retired": True,
    }


@endpoint([VIEW], {"GET"})
def status(request, server):
    with storage.enter_session() as sess:
        rows = sess.scalars(
            select(LeadershipVote)
            .where(LeadershipVote.server_number == server)
            .order_by(LeadershipVote.created_at.desc())
            .limit(100)
        ).all()
        result = {
            "enabled": False,
            "retired": True,
            "votes": [storage.summary(v) for v in rows],
        }
    audit(request, "status", server)
    return result


@endpoint([VIEW, CLAIM], {"POST"})
def cancel(request, server, vote_id):
    result = storage.cancel(server, str(vote_id), request.user.username)
    audit(request, "cancel", server, {"vote_id": str(vote_id)})
    return result


urlpatterns = [
    path("config", configuration),
    path("status", status),
    path("votes/<uuid:vote_id>/cancel", cancel),
]
