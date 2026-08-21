"""Authenticated API for the general setting-effect contract."""

from __future__ import annotations

import logging

from django.views.decorators.csrf import csrf_exempt
from sqlalchemy import func, select

from rcon.api_commands import get_rcon_api
from rcon.models import AuditLog, enter_session
from rcon.setting_effects import (
    GENERAL_SETTING_EFFECTS,
    build_setting_effects_snapshot,
    summarize_setting_audits,
)
from rcon.user_config.auto_settings import AutoSettingsConfig
from rcon.utils import get_server_number

from .auth import api_response, login_required
from .audit_log import record_audit
from .decorators import permission_required, require_http_methods
from .utils import _get_data

logger = logging.getLogger("rconweb")

rcon_api = get_rcon_api()


def _has_permission(user, permission: str) -> bool:
    return bool(user.is_superuser or user.has_perm(permission))


def _load_audit_summaries() -> dict:
    commands = [metadata["setter"] for metadata in GENERAL_SETTING_EFFECTS.values()]
    ranked = (
        select(
            AuditLog.id,
            AuditLog.username,
            AuditLog.creation_time,
            AuditLog.command,
            AuditLog.command_result,
            func.row_number()
            .over(partition_by=AuditLog.command, order_by=AuditLog.id.desc())
            .label("row_number"),
        )
        .where(AuditLog.command.in_(commands))
        .subquery()
    )
    statement = select(ranked).where(ranked.c.row_number <= 25)
    with enter_session() as session:
        records = session.execute(statement).all()
    return summarize_setting_audits(records, commands)


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def get_general_setting_effects(request):
    """Return live, permission-aware setting values and effect metadata."""

    auto_settings = None
    if _has_permission(request.user, "api.can_view_auto_settings"):
        try:
            auto_settings = AutoSettingsConfig().get_settings()
        except Exception:
            logger.exception("Unable to load Auto Settings effect metadata")
            auto_settings_state = "unavailable"
        else:
            auto_settings_state = "available"
    else:
        auto_settings_state = "permission_missing"

    audit_summaries = {}
    if _has_permission(request.user, "api.can_view_audit_logs"):
        try:
            audit_summaries = _load_audit_summaries()
        except Exception:
            logger.exception("Unable to load general setting audit provenance")
            audit_state = "unavailable"
        else:
            audit_state = "available"
    else:
        audit_state = "permission_missing"

    result = build_setting_effects_snapshot(
        rcon_api=rcon_api,
        user=request.user,
        server_number=int(get_server_number()),
        game=rcon_api.game_profile.game.value,
        auto_settings=auto_settings,
        auto_settings_state=auto_settings_state,
        audit_summaries=audit_summaries,
        audit_state=audit_state,
    )
    return api_response(
        result=result,
        command="get_general_setting_effects",
        failed=False,
    )


def _apply_and_confirm(request, *, setting_key: str):
    """Set a value and immediately read the authoritative game-server value."""
    metadata = GENERAL_SETTING_EFFECTS[setting_key]
    data = _get_data(request)
    requested = int(data[metadata["value_parameter"]])
    setter = getattr(rcon_api, metadata["setter"])
    getter = getattr(rcon_api, metadata["getter"])

    setter(requested)
    observed = getter()
    state = "confirmed" if observed == requested else "pending"
    return api_response(
        result={
            "setting": setting_key,
            "requested": requested,
            "observed": observed,
            "state": state,
            "reconcile": (
                "next_map_or_server_restart" if state == "pending" else None
            ),
        },
        command=f"apply_{setting_key}",
        failed=False,
    )


@csrf_exempt
@login_required()
@record_audit
@permission_required(
    {"api.can_change_queue_length", "api.can_view_queue_length"},
    raise_exception=True,
)
@require_http_methods(["POST"])
def apply_queue_length(request):
    return _apply_and_confirm(request, setting_key="queue_length")


@csrf_exempt
@login_required()
@record_audit
@permission_required(
    {"api.can_change_vip_slots", "api.can_view_vip_slots"},
    raise_exception=True,
)
@require_http_methods(["POST"])
def apply_vip_slots_num(request):
    return _apply_and_confirm(request, setting_key="vip_slots_num")
