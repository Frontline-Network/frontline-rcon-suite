from __future__ import annotations

from datetime import datetime, timezone

from django.views.decorators.csrf import csrf_exempt

from rcon.autobalancer.models import Phase
from rcon.autobalancer.repository import DecisionRepository
from rcon.autobalancer.store import AutobalancerStore
from rcon.user_config.autobalancer import AutobalancerUserConfig
from rcon.utils import get_server_number

from .audit_log import record_audit
from .auth import api_response, login_required
from .decorators import permission_required, require_http_methods
from .utils import _get_data


def _repository() -> DecisionRepository:
    return DecisionRepository(int(get_server_number()))


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def describe_autobalancer_config(request):
    return api_response(
        result=AutobalancerUserConfig.model_json_schema(),
        command="describe_autobalancer_config",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_config(request):
    return api_response(
        result=AutobalancerUserConfig.load_from_db(),
        command="get_autobalancer_config",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_change_autobalancer_config", raise_exception=True)
@require_http_methods(["POST"])
def validate_autobalancer_config(request):
    config = AutobalancerUserConfig.model_validate(_get_data(request))
    return api_response(
        result=config,
        command="validate_autobalancer_config",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_change_autobalancer_config", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
def set_autobalancer_config(request):
    data = _get_data(request)
    config = AutobalancerUserConfig.model_validate(data)
    config.save_to_db(config.model_dump(), dry_run=False)
    return api_response(
        result=config,
        command="set_autobalancer_config",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_status(request):
    return api_response(
        result=AutobalancerStore().load_status(),
        command="get_autobalancer_status",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_execute_autobalancer", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
def approve_autobalancer_proposal(request):
    data = _get_data(request)
    decision_id = str(data.get("decision_id") or "")
    store = AutobalancerStore()
    state = store.load_state()
    if (
        state.get("phase") != Phase.PROPOSED
        or state.get("decision_id") != decision_id
        or AutobalancerUserConfig.load_from_db().mode != "manual"
    ):
        return api_response(
            result=None,
            command="approve_autobalancer_proposal",
            failed=True,
            error="Proposal is no longer eligible for approval",
        )
    approved_at = datetime.now(timezone.utc).timestamp()
    state["approved_at"] = approved_at
    state["approved_by"] = request.user.username
    store.save_state(state)
    _repository().update(
        decision_id, status="approved", approved_by=request.user.username
    )
    store.publish_event(
        "approval",
        {
            "event_id": f"approval:{decision_id}",
            "decision_id": decision_id,
            "approved_at": approved_at,
            "approved_by": request.user.username,
        },
    )
    return api_response(
        result={"decision_id": decision_id, "status": "approved"},
        command="approve_autobalancer_proposal",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_execute_autobalancer", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
def cancel_autobalancer_incident(request):
    data = _get_data(request)
    incident_id = str(data.get("incident_id") or "")
    reason = str(data.get("reason") or "Manuell durch Admin abgebrochen")
    store = AutobalancerStore()
    state = store.load_state()
    if not incident_id or state.get("incident_id") != incident_id:
        return api_response(
            result=None,
            command="cancel_autobalancer_incident",
            failed=True,
            error="Incident is no longer active",
        )
    cancelled_at = datetime.now(timezone.utc).timestamp()
    config = AutobalancerUserConfig.load_from_db()
    store.arm_player(None)
    store.save_state(
        {
            "phase": Phase.COOLDOWN,
            "round_id": state.get("round_id"),
            "cooldown_started_at": cancelled_at,
            "cooldown_until": cancelled_at + config.stable_difference_seconds,
            "cancelled_by": request.user.username,
            "cancel_reason": reason,
        }
    )
    if state.get("decision_id"):
        _repository().update(
            state["decision_id"],
            status="aborted",
            approved_by=request.user.username,
            reason={
                "abort_reason": reason,
                "selection": (state.get("candidate") or {}).get("reason"),
                "plan": state.get("plan"),
            },
        )
    store.publish_event(
        "cancel",
        {
            "event_id": f"cancel:{incident_id}:{cancelled_at}",
            "incident_id": incident_id,
            "reason": reason,
            "cancelled_at": cancelled_at,
            "cancelled_by": request.user.username,
        },
    )
    return api_response(
        result={"incident_id": incident_id, "status": "aborted"},
        command="cancel_autobalancer_incident",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_history(request):
    data = _get_data(request)
    result = _repository().history(
        limit=int(data.get("limit") or 100),
        round_id=data.get("round_id") or None,
        status=data.get("status") or None,
    )
    return api_response(
        result=result,
        command="get_autobalancer_history",
        failed=False,
    )
