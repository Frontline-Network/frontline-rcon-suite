from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from django.views.decorators.csrf import csrf_exempt

from rcon.autobalancer.history import RoundHistoryRepository
from rcon.autobalancer.models import Phase
from rcon.autobalancer.repository import DecisionRepository
from rcon.autobalancer.store import AutobalancerStore
from rcon.user_config.autobalancer import AutobalancerUserConfig
from rcon.utils import get_server_number

from .audit_log import record_audit
from .auth import api_response, login_required
from .decorators import permission_required, require_http_methods
from .utils import _get_data


SHADOW_REJECTION_CATEGORIES = {
    "squad_should_stay",
    "critical_role",
    "recent_join_or_move",
    "better_candidate",
    "skill_balance",
    "wrong_team_counts",
    "other",
}


def validate_shadow_review(data):
    decision_id = str(data.get("decision_id") or "").strip()
    verdict = str(data.get("verdict") or "").strip().lower()
    category = str(data.get("category") or "").strip() or None
    comment = str(data.get("comment") or "").strip() or None
    if not decision_id:
        raise ValueError("decision_id fehlt")
    if verdict not in {"accepted", "rejected"}:
        raise ValueError("verdict muss accepted oder rejected sein")
    if verdict == "accepted":
        category = None
    elif category not in SHADOW_REJECTION_CATEGORIES:
        raise ValueError("Für eine Ablehnung ist ein gültiger Grund erforderlich")
    if comment and len(comment) > 1000:
        raise ValueError("Der Kommentar darf höchstens 1000 Zeichen lang sein")
    return decision_id, verdict, category, comment


def _repository() -> DecisionRepository:
    return DecisionRepository(int(get_server_number()))


def _history_date(value, *, end_of_day: bool = False):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if len(str(value)) == 10:
        parsed = datetime.combine(parsed.date(), time.min)
        if end_of_day:
            parsed += timedelta(days=1)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


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


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_shadow_overview(request):
    data = _get_data(request)
    try:
        limit = int(data.get("limit") or 200)
    except (TypeError, ValueError):
        limit = 200
    result = _repository().shadow_overview(
        limit=limit,
        round_id=data.get("round_id") or None,
    )
    try:
        timeline_limit = int(data.get("timeline_limit") or 720)
    except (TypeError, ValueError):
        timeline_limit = 720
    store = AutobalancerStore()
    result["live_status"] = store.load_status()
    result["timeline"] = store.load_status_history(limit=timeline_limit)
    return api_response(
        result=result,
        command="get_autobalancer_shadow_overview",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_round_archive(request):
    data = _get_data(request)
    try:
        page = int(data.get("page") or 1)
        limit = int(data.get("limit") or 12)
        map_id = int(data["map_id"]) if data.get("map_id") else None
        date_from = _history_date(data.get("date_from"))
        date_to = _history_date(data.get("date_to"), end_of_day=True)
    except (TypeError, ValueError):
        return api_response(
            result=None,
            command="get_autobalancer_round_archive",
            failed=True,
            error="Ungültige Suchparameter",
        )

    repository = RoundHistoryRepository(int(get_server_number()))
    result = repository.search(
        page=page,
        limit=limit,
        search=str(data.get("search") or "").strip() or None,
        date_from=date_from,
        date_to=date_to,
    )
    result["analysis"] = None
    if map_id is not None:
        config = AutobalancerUserConfig.load_from_db()
        result["analysis"] = repository.analyze(
            map_id,
            target_difference=config.target_difference,
            minimum_players=config.minimum_players,
            round_start_protection_seconds=config.map_start_grace_minutes * 60,
            round_end_protection_seconds=config.map_end_guard_minutes * 60,
            stable_difference_seconds=config.stable_difference_seconds,
        )
        if result["analysis"] is None:
            return api_response(
                result=None,
                command="get_autobalancer_round_archive",
                failed=True,
                error="Runde wurde auf diesem Server nicht gefunden",
            )

    return api_response(
        result=result,
        command="get_autobalancer_round_archive",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_view_autobalancer", raise_exception=True)
@require_http_methods(["GET"])
def get_autobalancer_history_dashboard(request):
    data = _get_data(request)
    config = AutobalancerUserConfig.load_from_db()
    try:
        days = int(data.get("days") or 90)
        limit = int(data.get("limit") or 100)
        target_difference = int(
            data.get("target_difference")
            if data.get("target_difference") not in {None, ""}
            else config.target_difference
        )
        stable_difference_seconds = int(
            data.get("stable_difference_seconds")
            if data.get("stable_difference_seconds") not in {None, ""}
            else config.stable_difference_seconds
        )
    except (TypeError, ValueError):
        return api_response(
            result=None,
            command="get_autobalancer_history_dashboard",
            failed=True,
            error="Ungültige Analyseparameter",
        )
    if not 0 <= target_difference <= 10 or not 15 <= stable_difference_seconds <= 300:
        return api_response(
            result=None,
            command="get_autobalancer_history_dashboard",
            failed=True,
            error="Zieldifferenz oder Stabilitätsdauer liegt außerhalb des gültigen Bereichs",
        )
    result = RoundHistoryRepository(int(get_server_number())).dashboard(
        target_difference=target_difference,
        minimum_players=config.minimum_players,
        round_start_protection_seconds=config.map_start_grace_minutes * 60,
        round_end_protection_seconds=config.map_end_guard_minutes * 60,
        stable_difference_seconds=stable_difference_seconds,
        days=days,
        search=str(data.get("search") or "").strip() or None,
        limit=limit,
    )
    return api_response(
        result=result,
        command="get_autobalancer_history_dashboard",
        failed=False,
    )


@csrf_exempt
@login_required()
@permission_required("api.can_execute_autobalancer", raise_exception=True)
@record_audit
@require_http_methods(["POST"])
def review_autobalancer_shadow_decision(request):
    try:
        decision_id, verdict, category, comment = validate_shadow_review(
            _get_data(request)
        )
    except ValueError as error:
        return api_response(
            result=None,
            command="review_autobalancer_shadow_decision",
            failed=True,
            error=str(error),
        )
    result = _repository().review_shadow_decision(
        decision_id=decision_id,
        verdict=verdict,
        category=category,
        comment=comment,
        reviewed_by=request.user.username,
    )
    if result is None:
        return api_response(
            result=None,
            command="review_autobalancer_shadow_decision",
            failed=True,
            error="Shadow-Vorschlag wurde nicht gefunden",
        )
    return api_response(
        result=result,
        command="review_autobalancer_shadow_decision",
        failed=False,
    )
