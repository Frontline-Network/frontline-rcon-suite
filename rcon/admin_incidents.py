import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select

from rcon.models import AdminIncident, AdminIncidentEvent, enter_session
from rcon.utils import get_server_number

INCIDENT_STATUSES = {"new", "claimed", "resolved", "dismissed"}
FINAL_STATUSES = {"resolved", "dismissed"}
DEFAULT_TRIGGER_WORDS = ("!admin",)


class IncidentNotFound(ValueError):
    pass


class IncidentConflict(ValueError):
    pass


class InvalidIncidentTransition(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _normalize_message(value: str) -> str:
    return " ".join(value.casefold().split())


def _dedupe_key(server_number: int, reporter_id: str | None, message: str) -> str:
    raw = f"{server_number}:{reporter_id or ''}:{_normalize_message(message)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _trigger_match(message: str, trigger_words: Iterable[str]):
    for trigger_word in sorted(trigger_words, key=len, reverse=True):
        trigger_word = trigger_word.strip()
        if not trigger_word:
            continue
        match = re.search(
            rf"(?<![\w]){re.escape(trigger_word)}(?![\w])",
            message,
            flags=re.IGNORECASE,
        )
        if match:
            return trigger_word, match
    return None, None


def parse_chat_report(
    message: str,
    trigger_words: Iterable[str] = DEFAULT_TRIGGER_WORDS,
    current_players: Sequence[dict] | None = None,
) -> dict | None:
    """Parse an admin trigger and only link a target when the match is unique."""

    trigger, match = _trigger_match(message, trigger_words)
    if not match:
        return None
    remainder = message[match.end() :].strip(" :-\t")
    if not remainder:
        remainder = "Admin assistance requested"

    target_id = None
    target_name = None
    reason = remainder
    candidates = []
    for player in current_players or ():
        name = str(player.get("name") or "").strip()
        if not name:
            continue
        if remainder.casefold() == name.casefold() or remainder.casefold().startswith(
            name.casefold() + " "
        ):
            candidates.append(player)
    if candidates:
        longest = max(len(str(player["name"])) for player in candidates)
        candidates = [
            player for player in candidates if len(str(player["name"])) == longest
        ]
    if len(candidates) == 1:
        target = candidates[0]
        target_id = str(target.get("player_id") or "") or None
        target_name = str(target.get("name") or "") or None
        reason = remainder[len(target_name or "") :].strip(" :-\t") or remainder

    return {
        "trigger": trigger,
        "target_id": target_id,
        "target_name": target_name,
        "reason": reason[:4000],
        "raw_message": message[:4000],
    }


def _event(
    actor: str, event_type: str, payload: dict | None = None
) -> AdminIncidentEvent:
    return AdminIncidentEvent(
        actor=actor,
        event_type=event_type,
        payload=payload or {},
    )


def create_incident(
    *,
    server_number: int,
    source: str,
    reason: str,
    actor: str,
    reporter_id: str | None = None,
    reporter_name: str | None = None,
    target_id: str | None = None,
    target_name: str | None = None,
    raw_message: str | None = None,
    dedupe_seconds: int = 60,
    idempotency_key: str | None = None,
) -> tuple[dict, bool]:
    if source not in {"chat", "manual"}:
        raise ValueError("Unsupported incident source")
    reason = reason.strip()
    if not reason:
        raise ValueError("Incident reason is required")
    if idempotency_key is not None and (
        not idempotency_key or len(idempotency_key) > 64
    ):
        raise ValueError("A valid Idempotency-Key header is required")

    now = _utcnow()
    dedupe_key = None
    if raw_message:
        dedupe_key = _dedupe_key(server_number, reporter_id, raw_message)

    with enter_session() as sess:
        if idempotency_key:
            existing_event = sess.execute(
                select(AdminIncidentEvent).where(
                    AdminIncidentEvent.idempotency_key == idempotency_key
                )
            ).scalar_one_or_none()
            if existing_event:
                return existing_event.incident.to_dict(include_events=True), False
        if dedupe_key:
            existing = sess.execute(
                select(AdminIncident).where(
                    AdminIncident.dedupe_key == dedupe_key,
                    AdminIncident.created_at >= now - timedelta(seconds=dedupe_seconds),
                )
            ).scalar_one_or_none()
            if existing:
                return existing.to_dict(include_events=True), False

        incident = AdminIncident(
            server_number=server_number,
            source=source,
            status="new",
            reporter_id=reporter_id,
            reporter_name=reporter_name,
            target_id=target_id,
            target_name=target_name,
            reason=reason[:4000],
            raw_message=(raw_message or "")[:4000] or None,
            dedupe_key=dedupe_key,
            revision=1,
            created_at=now,
            updated_at=now,
        )
        created_event = _event(
            actor,
            "created",
            {"source": source, "server_number": server_number},
        )
        created_event.idempotency_key = idempotency_key
        incident.events.append(created_event)
        sess.add(incident)
        sess.flush()
        result = incident.to_dict(include_events=True)
    return result, True


def create_incident_from_chat(
    log: dict,
    *,
    current_players: Sequence[dict] | None = None,
    trigger_words: Iterable[str] = DEFAULT_TRIGGER_WORDS,
) -> tuple[dict, bool] | None:
    parsed = parse_chat_report(
        str(log.get("sub_content") or ""),
        trigger_words=trigger_words,
        current_players=current_players,
    )
    if not parsed:
        return None
    return create_incident(
        server_number=int(get_server_number()),
        source="chat",
        reason=parsed["reason"],
        raw_message=parsed["raw_message"],
        actor="system:chat",
        reporter_id=str(log.get("player_id_1") or "") or None,
        reporter_name=str(log.get("player_name_1") or "") or None,
        target_id=parsed["target_id"],
        target_name=parsed["target_name"],
    )


def list_incidents(
    *,
    statuses: Iterable[str] | None = None,
    server_numbers: Iterable[int] | None = None,
    assigned_to: str | None = None,
    updated_after: datetime | None = None,
    limit: int = 100,
) -> list[dict]:
    limit = min(max(limit, 1), 250)
    stmt = select(AdminIncident)
    if statuses:
        normalized = set(statuses)
        if not normalized.issubset(INCIDENT_STATUSES):
            raise ValueError("Unknown incident status")
        stmt = stmt.where(AdminIncident.status.in_(normalized))
    if server_numbers:
        stmt = stmt.where(AdminIncident.server_number.in_(set(server_numbers)))
    if assigned_to:
        stmt = stmt.where(AdminIncident.assigned_to == assigned_to)
    if updated_after:
        stmt = stmt.where(AdminIncident.updated_at > updated_after)
    stmt = stmt.order_by(
        AdminIncident.updated_at.desc(), AdminIncident.id.desc()
    ).limit(limit)
    with enter_session() as sess:
        return [incident.to_dict() for incident in sess.execute(stmt).scalars().all()]


def latest_incident_event_cursor() -> int:
    with enter_session() as sess:
        return int(
            sess.execute(select(func.max(AdminIncidentEvent.id))).scalar_one_or_none()
            or 0
        )


def list_incident_changes(
    after_event_id: int, *, limit: int = 100
) -> tuple[list[dict], int]:
    """Return changed incidents and an event cursor that cannot skip timestamp ties."""

    limit = min(max(limit, 1), 250)
    with enter_session() as sess:
        events = (
            sess.execute(
                select(AdminIncidentEvent)
                .where(AdminIncidentEvent.id > max(after_event_id, 0))
                .order_by(AdminIncidentEvent.id.asc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        if not events:
            return [], max(after_event_id, 0)
        incident_ids = list(dict.fromkeys(event.incident_id for event in events))
        incidents = {
            incident.id: incident
            for incident in sess.execute(
                select(AdminIncident).where(AdminIncident.id.in_(incident_ids))
            )
            .scalars()
            .all()
        }
        return (
            [
                incidents[incident_id].to_dict()
                for incident_id in incident_ids
                if incident_id in incidents
            ],
            events[-1].id,
        )


def get_incident(incident_id: str) -> dict:
    with enter_session() as sess:
        incident = sess.get(AdminIncident, incident_id)
        if not incident:
            raise IncidentNotFound("Incident not found")
        return incident.to_dict(include_events=True)


def mutate_incident(
    incident_id: str,
    *,
    actor: str,
    expected_revision: int,
    operation: str,
    payload: dict | None = None,
    idempotency_key: str | None = None,
) -> dict:
    payload = payload or {}
    if idempotency_key is not None and (
        not idempotency_key or len(idempotency_key) > 64
    ):
        raise ValueError("A valid Idempotency-Key header is required")
    now = _utcnow()
    with enter_session() as sess:
        if idempotency_key:
            existing_event = sess.execute(
                select(AdminIncidentEvent).where(
                    AdminIncidentEvent.idempotency_key == idempotency_key
                )
            ).scalar_one_or_none()
            if existing_event:
                if existing_event.incident_id != incident_id:
                    raise IncidentConflict(
                        "Idempotency key belongs to another incident"
                    )
                return existing_event.incident.to_dict(include_events=True)
        incident = sess.execute(
            select(AdminIncident)
            .where(AdminIncident.id == incident_id)
            .with_for_update()
        ).scalar_one_or_none()
        if not incident:
            raise IncidentNotFound("Incident not found")
        if incident.revision != expected_revision:
            raise IncidentConflict(
                f"Incident revision changed from {expected_revision} to {incident.revision}"
            )

        if operation == "claim":
            if incident.status not in {"new", "claimed"}:
                raise InvalidIncidentTransition("Only open incidents can be claimed")
            if incident.assigned_to and incident.assigned_to != actor:
                raise IncidentConflict("Incident is already claimed by another admin")
            incident.status = "claimed"
            incident.assigned_to = actor
        elif operation == "unclaim":
            if incident.status != "claimed":
                raise InvalidIncidentTransition("Incident is not claimed")
            if incident.assigned_to != actor:
                raise IncidentConflict(
                    "Only the assigned admin can release this incident"
                )
            incident.status = "new"
            incident.assigned_to = None
        elif operation in FINAL_STATUSES:
            if incident.status not in {"new", "claimed"}:
                raise InvalidIncidentTransition("Incident is already closed")
            incident.status = operation
            incident.resolved_at = now
        elif operation == "reopen":
            if incident.status not in FINAL_STATUSES:
                raise InvalidIncidentTransition("Only closed incidents can be reopened")
            incident.status = "new"
            incident.assigned_to = None
            incident.resolved_at = None
        elif operation == "reassign":
            assigned_to = str(payload.get("assigned_to") or "").strip()
            if not assigned_to:
                raise ValueError("assigned_to is required")
            incident.status = "claimed"
            incident.assigned_to = assigned_to[:150]
        elif operation == "link_target":
            target_id = str(payload.get("target_id") or "").strip()
            target_name = str(payload.get("target_name") or "").strip()
            if not target_id or not target_name:
                raise ValueError("target_id and target_name are required")
            incident.target_id = target_id[:100]
            incident.target_name = target_name[:255]
        elif operation == "note":
            note = str(payload.get("note") or "").strip()
            if not note:
                raise ValueError("Note cannot be empty")
            payload = {"note": note[:4000]}
        else:
            raise ValueError("Unsupported incident operation")

        incident.revision += 1
        incident.updated_at = now
        event = _event(actor, operation, payload)
        event.idempotency_key = idempotency_key
        incident.events.append(event)
        sess.flush()
        return incident.to_dict(include_events=True)


def reserve_incident_action(
    incident_id: str,
    *,
    actor: str,
    action: str,
    arguments: dict,
    idempotency_key: str,
) -> tuple[dict, bool]:
    if not idempotency_key or len(idempotency_key) > 64:
        raise ValueError("A valid Idempotency-Key header is required")
    with enter_session() as sess:
        existing = sess.execute(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if existing:
            for event in existing.incident.events:
                if (
                    event.event_type in {"action", "action_failed"}
                    and event.payload.get("idempotency_key") == idempotency_key
                ):
                    return event.to_dict(), False
            return existing.to_dict(), False
        incident = sess.execute(
            select(AdminIncident)
            .where(AdminIncident.id == incident_id)
            .with_for_update()
        ).scalar_one_or_none()
        if not incident:
            raise IncidentNotFound("Incident not found")
        safe_arguments = {
            key: value
            for key, value in arguments.items()
            if key not in {"token", "access_token", "refresh_token", "push_handle"}
        }
        event = _event(
            actor,
            "action_started",
            {"action": action, "arguments": safe_arguments},
        )
        event.idempotency_key = idempotency_key
        incident.events.append(event)
        incident.revision += 1
        incident.updated_at = _utcnow()
        sess.flush()
        return event.to_dict(), True


def complete_incident_action(
    idempotency_key: str, *, result: object = None, error: str | None = None
) -> dict:
    with enter_session() as sess:
        reservation = sess.execute(
            select(AdminIncidentEvent)
            .where(AdminIncidentEvent.idempotency_key == idempotency_key)
            .with_for_update()
        ).scalar_one_or_none()
        if not reservation:
            raise IncidentNotFound("Reserved incident action not found")
        for event in reservation.incident.events:
            if (
                event.event_type in {"action", "action_failed"}
                and event.payload.get("idempotency_key") == idempotency_key
            ):
                return reservation.incident.to_dict(include_events=True)
        outcome = _event(
            reservation.actor,
            "action_failed" if error else "action",
            {
                **reservation.payload,
                "idempotency_key": idempotency_key,
                "result": result,
                "error": error,
            },
        )
        reservation.incident.events.append(outcome)
        reservation.incident.revision += 1
        reservation.incident.updated_at = _utcnow()
        sess.flush()
        return reservation.incident.to_dict(include_events=True)


def purge_old_incidents(retention_days: int = 90) -> int:
    cutoff = _utcnow() - timedelta(days=max(retention_days, 1))
    with enter_session() as sess:
        result = sess.execute(
            delete(AdminIncident).where(AdminIncident.updated_at < cutoff)
        )
        return result.rowcount or 0
