"""Private, durable Eventador match-control API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import timedelta
from datetime import timezone as dt_timezone
from functools import wraps
from typing import Any, Callable

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from rconweb.settings import SECRET_KEY

from .auth import api_response
from .decorators import require_http_methods
from .eventador_control_contract import (
    EXECUTE_EARLY_TOLERANCE_SECONDS,
    EXECUTE_LATE_TOLERANCE_SECONDS,
    MUTATING_ACTIONS,
    PREPARE_TTL_SECONDS,
    ActionOutcomeUnknown,
    ContractError,
    KnownActionFailure,
    build_capabilities,
    build_state,
    digest,
    execute_game_action,
    parse_timestamp,
    runtime_scope_matches,
    schedule_conflict,
    state_matches_plan,
    validate_plan,
)
from .models import DjangoAPIKey, EventadorControlStep
from .ratelimits import request_rate_limit_key
from .views import rcon_api

logger = logging.getLogger("rconweb")
PERMISSION = "api.can_control_eventador_events"
MAX_REQUEST_BYTES = 64 * 1024
STATE_MAX_AGE_SECONDS = 30
EXECUTION_UNKNOWN_AFTER_SECONDS = 30


class ControlHttpError(Exception):
    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


def execution_enabled() -> bool:
    """Require the exact lowercase opt-in; invalid values fail closed."""

    return os.getenv("EVENTADOR_CONTROL_ENABLED", "false") == "true"


def _error(command: str, error: ControlHttpError) -> HttpResponse:
    return api_response(
        command=command,
        failed=True,
        error=error.message,
        status_code=error.status,
    )


def _service_key_required(command: str):
    """Accept only a revocable Django API key with the dedicated permission."""

    def decorator(view: Callable[..., HttpResponse]):
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            authorization = request.META.get("HTTP_AUTHORIZATION", "")
            try:
                scheme, raw_key = authorization.split(maxsplit=1)
            except ValueError:
                return _error(
                    command,
                    ControlHttpError(
                        "unauthorized", 401, "A bearer API key is required"
                    ),
                )
            if (
                scheme != "Bearer"
                or not 16 <= len(raw_key) <= 512
                or any(character.isspace() for character in raw_key)
            ):
                return _error(
                    command,
                    ControlHttpError(
                        "unauthorized", 401, "A bearer API key is required"
                    ),
                )
            encoded = make_password(raw_key, salt=SECRET_KEY.replace("$", ""))
            try:
                key = DjangoAPIKey.objects.select_related("user").get(api_key=encoded)
            except DjangoAPIKey.DoesNotExist:
                return _error(
                    command,
                    ControlHttpError("unauthorized", 401, "The API key is invalid"),
                )
            request.user = key.user
            request.eventador_api_key_id = key.pk
            if not key.user.is_active:
                return _error(
                    command,
                    ControlHttpError(
                        "unauthorized", 401, "The service identity is inactive"
                    ),
                )
            explicit_permissions = set(
                key.user.user_permissions.values_list(
                    "content_type__app_label", "codename"
                )
            )
            identity_scope_is_exact = (
                not key.user.is_staff
                and not key.user.is_superuser
                and not key.user.groups.exists()
                and explicit_permissions == {("api", "can_control_eventador_events")}
            )
            if not identity_scope_is_exact or not key.user.has_perm(PERMISSION):
                return _error(
                    command,
                    ControlHttpError(
                        "forbidden",
                        403,
                        "The API key lacks the exact Eventador permission scope",
                    ),
                )
            try:
                return view(request, *args, **kwargs)
            except ControlHttpError as exc:
                return _error(command, exc)
            except ContractError as exc:
                return _error(
                    command, ControlHttpError("invalid_request", 400, str(exc))
                )
            except Exception:
                logger.exception(
                    "Unexpected Eventador control API error in %s", view.__name__
                )
                return _error(
                    command,
                    ControlHttpError(
                        "internal_error", 500, "The control provider failed"
                    ),
                )

        return wrapper

    return decorator


def _json_body(request: HttpRequest) -> dict[str, Any]:
    if request.content_type != "application/json":
        raise ControlHttpError(
            "invalid_content_type", 400, "Content-Type must be application/json"
        )
    if len(request.body) > MAX_REQUEST_BYTES:
        raise ControlHttpError("request_too_large", 400, "The request is too large")
    try:
        value = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ControlHttpError(
            "invalid_json", 400, "The request body is invalid"
        ) from exc
    if not isinstance(value, dict):
        raise ControlHttpError(
            "invalid_json", 400, "The request body must be an object"
        )
    return value


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _confirmation_token(step: EventadorControlStep) -> str:
    message = f"eventador-control-v1:{step.id}:{step.plan_digest}".encode("ascii")
    raw = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _serialize_step(
    step: EventadorControlStep,
    *,
    cached: bool,
    include_confirmation: bool = False,
) -> dict[str, Any]:
    plan = step.plan
    result = {
        "preparation_id": str(step.id),
        "event_id": str(step.event_id),
        "event_revision": step.event_revision,
        "workflow_revision": step.workflow_revision,
        "step_id": step.step_id,
        "idempotency_key": str(step.idempotency_key),
        "target": plan["target"],
        "action": plan["action"],
        "reason": plan["reason"],
        "state": step.state,
        "execute_at": _iso(step.execute_at),
        "expires_at": _iso(step.expires_at),
        "execution_started_at": _iso(step.execution_started_at),
        "finished_at": _iso(step.finished_at),
        "result": step.result or {},
        "error_code": step.error_code,
        "confirmation_required": step.state == EventadorControlStep.State.PREPARED,
        "requires_second_confirmation": plan["action"] in MUTATING_ACTIONS,
        "cached": cached,
    }
    if include_confirmation and step.state == EventadorControlStep.State.PREPARED:
        result["confirmation_token"] = _confirmation_token(step)
    return result


def _step_response(
    command: str,
    step: EventadorControlStep,
    *,
    cached: bool,
    include_confirmation: bool = False,
) -> HttpResponse:
    return api_response(
        command=command,
        failed=False,
        result=_serialize_step(
            step, cached=cached, include_confirmation=include_confirmation
        ),
    )


def _existing_for_plan(plan: dict[str, Any], plan_digest: str):
    existing = EventadorControlStep.objects.filter(
        idempotency_key=plan["idempotency_key"]
    ).first()
    if existing:
        if existing.plan_digest != plan_digest:
            raise ControlHttpError(
                "idempotency_conflict", 409, "The idempotency key is already bound"
            )
        return existing
    scoped = EventadorControlStep.objects.filter(
        event_id=plan["event_id"],
        workflow_revision=plan["workflow_revision"],
        step_id=plan["step_id"],
    ).first()
    if scoped:
        raise ControlHttpError(
            "step_scope_conflict", 409, "The workflow step is already bound"
        )
    return None


def _finish(
    step_id,
    state: str,
    *,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> EventadorControlStep:
    with transaction.atomic():
        step = EventadorControlStep.objects.select_for_update().get(pk=step_id)
        if step.state != EventadorControlStep.State.EXECUTING:
            return step
        step.state = state
        step.finished_at = timezone.now()
        step.result = result or {}
        step.error_code = error_code
        step.save(
            update_fields=("state", "finished_at", "result", "error_code", "updated_at")
        )
        return step


@csrf_exempt
@require_http_methods(["GET"])
@ratelimit(
    group="eventador-control-read", key=request_rate_limit_key, rate="120/m", block=True
)
@_service_key_required("get_eventador_control_capabilities")
def capabilities(_request: HttpRequest) -> HttpResponse:
    return api_response(
        command="get_eventador_control_capabilities",
        failed=False,
        result=build_capabilities(rcon_api, execution_enabled()),
    )


@csrf_exempt
@require_http_methods(["GET"])
@ratelimit(
    group="eventador-control-state", key=request_rate_limit_key, rate="60/m", block=True
)
@_service_key_required("get_eventador_control_state")
def state(_request: HttpRequest) -> HttpResponse:
    return api_response(
        command="get_eventador_control_state",
        failed=False,
        result=build_state(rcon_api),
    )


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(
    group="eventador-control-prepare",
    key=request_rate_limit_key,
    rate="30/m",
    block=True,
)
@_service_key_required("prepare_eventador_control_step")
def prepare_step(request: HttpRequest) -> HttpResponse:
    command = "prepare_eventador_control_step"
    if not execution_enabled():
        raise ControlHttpError(
            "execution_disabled", 409, "Eventador control execution is disabled"
        )
    plan = validate_plan(_json_body(request))
    plan_digest = digest(plan)
    with transaction.atomic():
        existing = _existing_for_plan(plan, plan_digest)
        if existing:
            return _step_response(
                command,
                existing,
                cached=True,
                include_confirmation=True,
            )

    now = timezone.now()
    execute_at = parse_timestamp(plan["execute_at"], "execute_at")
    observed_at = parse_timestamp(
        plan["expected"]["state_observed_at"], "expected.state_observed_at"
    )
    too_old = (now - observed_at).total_seconds() > STATE_MAX_AGE_SECONDS
    from_future = (observed_at - now).total_seconds() > 5
    current = build_state(rcon_api, captured_at=now)
    previous_step_id = plan["expected"]["previous_step_id"]
    previous_succeeded = True
    if previous_step_id is not None:
        previous_succeeded = EventadorControlStep.objects.filter(
            event_id=plan["event_id"],
            event_revision=plan["event_revision"],
            workflow_revision=plan["workflow_revision"],
            step_id=previous_step_id,
            state=EventadorControlStep.State.SUCCEEDED,
        ).exists()
    revision_consistent = (
        not EventadorControlStep.objects.filter(
            event_id=plan["event_id"], workflow_revision=plan["workflow_revision"]
        )
        .exclude(event_revision=plan["event_revision"])
        .exists()
    )
    conflict_code = schedule_conflict(now, execute_at)
    if too_old:
        conflict_code = conflict_code or "state_observation_stale"
    if from_future:
        conflict_code = conflict_code or "state_observation_future"
    if not previous_succeeded:
        conflict_code = conflict_code or "previous_step_not_succeeded"
    if not revision_consistent:
        conflict_code = conflict_code or "event_revision_conflict"
    if not state_matches_plan(current, plan):
        conflict_code = conflict_code or "state_conflict"
    if not runtime_scope_matches(rcon_api, current, plan):
        conflict_code = conflict_code or "action_scope_conflict"
    conflict = conflict_code is not None
    try:
        with transaction.atomic():
            existing = _existing_for_plan(plan, plan_digest)
            if existing:
                return _step_response(
                    command,
                    existing,
                    cached=True,
                    include_confirmation=True,
                )
            step = EventadorControlStep.objects.create(
                event_id=plan["event_id"],
                event_revision=plan["event_revision"],
                workflow_revision=plan["workflow_revision"],
                step_id=plan["step_id"],
                idempotency_key=plan["idempotency_key"],
                plan=plan,
                plan_digest=plan_digest,
                prepared_by=request.user.username[:150],
                state=(
                    EventadorControlStep.State.CONFLICT
                    if conflict
                    else EventadorControlStep.State.PREPARED
                ),
                execute_at=execute_at,
                expires_at=min(
                    now + timedelta(seconds=PREPARE_TTL_SECONDS),
                    execute_at + timedelta(seconds=EXECUTE_LATE_TOLERANCE_SECONDS),
                ),
                finished_at=now if conflict else None,
                error_code=conflict_code,
            )
    except IntegrityError as exc:
        existing = _existing_for_plan(plan, plan_digest)
        if not existing:
            raise exc
        step = existing
        return _step_response(command, step, cached=True, include_confirmation=True)
    return _step_response(
        command, step, cached=False, include_confirmation=not conflict
    )


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(
    group="eventador-control-execute",
    key=request_rate_limit_key,
    rate="30/m",
    block=True,
)
@_service_key_required("execute_eventador_control_step")
def execute_step(request: HttpRequest, preparation_id) -> HttpResponse:
    command = "execute_eventador_control_step"
    data = _json_body(request)
    if set(data) != {"confirmation_token"}:
        raise ControlHttpError(
            "invalid_request", 400, "Only confirmation_token is accepted"
        )
    token = data["confirmation_token"]
    if not isinstance(token, str) or not 16 <= len(token) <= 255:
        raise ControlHttpError(
            "invalid_confirmation", 403, "The confirmation token is invalid"
        )
    if not execution_enabled():
        raise ControlHttpError(
            "execution_disabled", 409, "Eventador control execution is disabled"
        )

    with transaction.atomic():
        try:
            step = EventadorControlStep.objects.select_for_update().get(
                pk=preparation_id
            )
        except EventadorControlStep.DoesNotExist as exc:
            raise ControlHttpError(
                "not_found", 404, "The preparation was not found"
            ) from exc
        if step.state != EventadorControlStep.State.PREPARED:
            return _step_response(command, step, cached=True)
        now = timezone.now()
        if now < step.execute_at - timedelta(seconds=EXECUTE_EARLY_TOLERANCE_SECONDS):
            raise ControlHttpError(
                "execution_not_due", 409, "The preparation is not due yet"
            )
        if step.expires_at <= now:
            step.state = EventadorControlStep.State.FAILED
            step.finished_at = now
            step.error_code = "preparation_expired"
            step.save(
                update_fields=("state", "finished_at", "error_code", "updated_at")
            )
            return _step_response(command, step, cached=False)
        if not hmac.compare_digest(token, _confirmation_token(step)):
            raise ControlHttpError(
                "invalid_confirmation", 403, "The confirmation token is invalid"
            )
        previous_step_id = step.plan["expected"]["previous_step_id"]
        previous_succeeded = (
            previous_step_id is None
            or EventadorControlStep.objects.filter(
                event_id=step.event_id,
                event_revision=step.event_revision,
                workflow_revision=step.workflow_revision,
                step_id=previous_step_id,
                state=EventadorControlStep.State.SUCCEEDED,
            ).exists()
        )
        revision_consistent = (
            not EventadorControlStep.objects.filter(
                event_id=step.event_id,
                workflow_revision=step.workflow_revision,
            )
            .exclude(event_revision=step.event_revision)
            .exists()
        )
        if not previous_succeeded or not revision_consistent:
            step.state = EventadorControlStep.State.CONFLICT
            step.finished_at = now
            step.error_code = (
                "previous_step_not_succeeded"
                if not previous_succeeded
                else "event_revision_conflict"
            )
            step.save(
                update_fields=("state", "finished_at", "error_code", "updated_at")
            )
            return _step_response(command, step, cached=False)
        step.state = EventadorControlStep.State.EXECUTING
        step.execution_started_at = now
        step.save(update_fields=("state", "execution_started_at", "updated_at"))

    try:
        current = build_state(rcon_api)
    except Exception:
        logger.exception("Unable to capture Eventador execution precondition")
        step = _finish(
            step.id,
            EventadorControlStep.State.FAILED,
            error_code="state_unavailable",
        )
        return _step_response(command, step, cached=False)
    if not state_matches_plan(current, step.plan) or not runtime_scope_matches(
        rcon_api, current, step.plan
    ):
        step = _finish(
            step.id,
            EventadorControlStep.State.CONFLICT,
            error_code="state_conflict",
        )
        return _step_response(command, step, cached=False)

    try:
        result = execute_game_action(rcon_api, step.plan)
    except KnownActionFailure as exc:
        step = _finish(
            step.id,
            EventadorControlStep.State.FAILED,
            result=exc.result,
            error_code="action_rejected",
        )
        return _step_response(command, step, cached=False)
    except ActionOutcomeUnknown as exc:
        logger.exception(
            "Eventador control action has an unknown outcome for preparation %s",
            step.id,
        )
        step = _finish(
            step.id,
            EventadorControlStep.State.UNKNOWN,
            result=exc.result,
            error_code="execution_outcome_unknown",
        )
        return _step_response(command, step, cached=False)
    except Exception:
        logger.exception(
            "Eventador control action has an unknown outcome for preparation %s",
            step.id,
        )
        step = _finish(
            step.id,
            EventadorControlStep.State.UNKNOWN,
            error_code="execution_outcome_unknown",
        )
        return _step_response(command, step, cached=False)
    step = _finish(step.id, EventadorControlStep.State.SUCCEEDED, result=result)
    return _step_response(command, step, cached=False)


@csrf_exempt
@require_http_methods(["GET"])
@ratelimit(
    group="eventador-control-result",
    key=request_rate_limit_key,
    rate="120/m",
    block=True,
)
@_service_key_required("get_eventador_control_result")
def result(_request: HttpRequest, idempotency_key) -> HttpResponse:
    command = "get_eventador_control_result"
    with transaction.atomic():
        try:
            step = EventadorControlStep.objects.select_for_update().get(
                idempotency_key=idempotency_key
            )
        except EventadorControlStep.DoesNotExist as exc:
            raise ControlHttpError(
                "not_found", 404, "The result was not found"
            ) from exc
        if (
            step.state == EventadorControlStep.State.EXECUTING
            and step.execution_started_at
            and timezone.now() - step.execution_started_at
            > timedelta(seconds=EXECUTION_UNKNOWN_AFTER_SECONDS)
        ):
            step.state = EventadorControlStep.State.UNKNOWN
            step.finished_at = timezone.now()
            step.error_code = "execution_outcome_unknown"
            step.save(
                update_fields=("state", "finished_at", "error_code", "updated_at")
            )
    return _step_response(command, step, cached=True)
