import hashlib
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Iterable, Sequence

from sqlalchemy import delete, func, select

from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    AdminIncidentSubject,
    enter_session,
)
from rcon.utils import get_server_number

INCIDENT_STATUSES = {"new", "claimed", "resolved", "dismissed"}
FINAL_STATUSES = {"resolved", "dismissed"}
DEFAULT_TRIGGER_WORDS = ("!admin",)
SUBJECT_KINDS = {"player", "squad"}
SUBJECT_STATES = {"suggested", "confirmed", "rejected"}
PARSER_VERSION = "2.0.0"
DEFAULT_FUZZY_THRESHOLD = 0.74


def _mobile_context_fuzzy_threshold() -> float:
    try:
        value = float(
            os.getenv("MOBILE_CONTEXT_FUZZY_THRESHOLD", str(DEFAULT_FUZZY_THRESHOLD))
        )
    except (TypeError, ValueError):
        value = DEFAULT_FUZZY_THRESHOLD
    return max(0.0, min(value, 1.0))


class IncidentNotFound(ValueError):
    pass


class IncidentConflict(ValueError):
    pass


class InvalidIncidentTransition(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _normalize_message(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def _normalize_team(value: Any) -> str:
    """Normalize CRCON team values without assuming their representation."""

    normalized = _normalize_message(str(value or ""))
    tail = normalized.split()[-1] if normalized else ""
    aliases = {
        "allied": "allies",
        "allies": "allies",
        "axis": "axis",
    }
    return aliases.get(tail, tail)


def _strip_clan_tag(value: str) -> str:
    return re.sub(r"^\s*(?:\[[^\]]+\]|<[^>]+>|\([^\)]+\))\s*", "", value).strip()


def _simple_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def player_snapshot(player: dict | None) -> dict:
    if not player:
        return {}
    fields = (
        "player_id",
        "name",
        "team",
        "faction",
        "unit_id",
        "unit_name",
        "role",
        "loadout",
        "level",
        "kills",
        "deaths",
        "teamkills",
        "combat",
        "offense",
        "defense",
        "support",
        "map_playtime_seconds",
        "is_vip",
    )
    return {
        field: _simple_value(player.get(field))
        for field in fields
        if player.get(field) is not None
    }


def flatten_team_view(team_view: dict | None) -> list[dict]:
    squads = []
    for team_name, team in (team_view or {}).items():
        if team_name == "fail_count" or not isinstance(team, dict):
            continue
        for squad_name, squad in (team.get("squads") or {}).items():
            if not isinstance(squad, dict):
                continue
            players = [player_snapshot(player) for player in squad.get("players", [])]
            leader = next(
                (
                    player
                    for player in players
                    if str(player.get("role") or "").casefold()
                    in {"officer", "tankcommander", "spotter"}
                ),
                None,
            )
            squads.append(
                {
                    "name": str(squad_name or "Unassigned"),
                    "team": str(team_name),
                    "type": squad.get("type"),
                    "has_leader": bool(squad.get("has_leader")),
                    "leader": leader,
                    "players": players,
                }
            )
    return squads


def _best_fuzzy_window(query: str, text: str) -> tuple[float, str]:
    query_words = query.split()
    text_words = text.split()
    if not query_words or not text_words:
        return 0.0, ""
    sizes = {max(1, len(query_words) - 1), len(query_words), len(query_words) + 1}
    best = (0.0, "")
    for size in sizes:
        for index in range(max(1, len(text_words) - size + 1)):
            candidate = " ".join(text_words[index : index + size])
            score = SequenceMatcher(None, query, candidate).ratio()
            if score > best[0]:
                best = (score, candidate)
    return best


def _subject_key(subject: dict) -> tuple:
    if subject["kind"] == "player":
        return ("player", subject.get("player_id") or subject["display_name"])
    return ("squad", subject.get("team"), subject.get("squad_name"))


def _resolve_subjects(
    remainder: str,
    *,
    current_players: Sequence[dict],
    current_squads: Sequence[dict],
    reporter_context: dict,
    fuzzy_threshold: float,
    shadow: bool,
) -> list[dict]:
    normalized_message = _normalize_message(remainder)
    candidates: list[dict] = []
    player_names: dict[str, list[dict]] = {}
    for player in current_players:
        name = str(player.get("name") or player.get("player_name") or "").strip()
        if name:
            player_names.setdefault(_normalize_message(name), []).append(player)

    for normalized_name, matching_players in player_names.items():
        if len(normalized_name) < 3:
            continue
        exact = re.search(
            rf"(?<!\w){re.escape(normalized_name)}(?!\w)", normalized_message
        )
        for player in matching_players:
            name = str(player.get("name") or player.get("player_name") or "").strip()
            state = "confirmed" if exact and len(matching_players) == 1 else "suggested"
            method = "name_contained" if exact else ""
            confidence = 1.0 if exact else 0.0
            matched_text = exact.group(0) if exact else ""
            if not exact:
                stripped = _normalize_message(_strip_clan_tag(name))
                clan_match = stripped and re.search(
                    rf"(?<!\w){re.escape(stripped)}(?!\w)", normalized_message
                )
                if clan_match and stripped != normalized_name:
                    method = "clan_tag_variant"
                    confidence = 0.9
                    matched_text = clan_match.group(0)
                else:
                    confidence, matched_text = _best_fuzzy_window(
                        stripped or normalized_name, normalized_message
                    )
                    if confidence < fuzzy_threshold:
                        continue
                    method = "fuzzy"
            snapshot = player_snapshot(player)
            candidates.append(
                {
                    "kind": "player",
                    "state": "suggested" if shadow else state,
                    "is_primary": False,
                    "display_name": name,
                    "player_id": str(player.get("player_id") or "") or None,
                    "team": player.get("team"),
                    "squad_name": player.get("unit_name"),
                    "squad_id": _simple_value(player.get("unit_id")),
                    "role": player.get("role"),
                    "confidence": round(confidence, 4),
                    "match_method": method,
                    "matched_text": matched_text,
                    "parser_version": PARSER_VERSION,
                    "snapshot": snapshot,
                    "_position": (
                        exact.start()
                        if exact
                        else normalized_message.find(matched_text)
                    ),
                    "_match_length": len(matched_text),
                }
            )

    reporter_team = str(reporter_context.get("team") or "")
    normalized_reporter_team = _normalize_team(reporter_team)
    squad_names: dict[tuple[str, str], list[dict]] = {}
    for squad in current_squads:
        name = str(squad.get("name") or squad.get("squad_name") or "").strip()
        team = str(squad.get("team") or "")
        if name:
            squad_names.setdefault((team, _normalize_message(name)), []).append(squad)
    for (team, normalized_name), matching_squads in squad_names.items():
        if len(normalized_name) < 3 or (
            normalized_reporter_team
            and _normalize_team(team) != normalized_reporter_team
        ):
            continue
        exact = re.search(
            rf"(?<!\w){re.escape(normalized_name)}(?!\w)", normalized_message
        )
        if not exact:
            confidence, matched_text = _best_fuzzy_window(
                normalized_name, normalized_message
            )
            if confidence < fuzzy_threshold:
                continue
            method = "squad_fuzzy"
        else:
            confidence, matched_text, method = 1.0, exact.group(0), "squad_exact"
        unique = len(matching_squads) == 1 and (
            bool(normalized_reporter_team)
            or sum(
                1
                for candidate_team, candidate_name in squad_names
                if candidate_name == normalized_name
            )
            == 1
        )
        for squad in matching_squads:
            leader = squad.get("leader") or {}
            players = [player_snapshot(player) for player in squad.get("players", [])]
            candidates.append(
                {
                    "kind": "squad",
                    "state": (
                        "confirmed" if exact and unique and not shadow else "suggested"
                    ),
                    "is_primary": False,
                    "display_name": str(squad.get("name")),
                    "team": team or None,
                    "squad_name": str(squad.get("name")),
                    "squad_type": squad.get("type"),
                    "leader_player_id": leader.get("player_id"),
                    "leader_name": leader.get("name"),
                    "confidence": round(confidence, 4),
                    "match_method": method,
                    "matched_text": matched_text,
                    "parser_version": PARSER_VERSION,
                    "snapshot": {
                        "team": team,
                        "squad_name": squad.get("name"),
                        "squad_type": squad.get("type"),
                        "has_leader": bool(squad.get("has_leader")),
                        "leader": player_snapshot(leader),
                        "players": players,
                    },
                    "_position": (
                        exact.start()
                        if exact
                        else normalized_message.find(matched_text)
                    ),
                    "_match_length": len(matched_text),
                }
            )

    deduplicated: dict[tuple, dict] = {}
    for candidate in candidates:
        key = _subject_key(candidate)
        existing = deduplicated.get(key)
        if not existing or candidate["confidence"] > existing["confidence"]:
            deduplicated[key] = candidate
    result = sorted(
        deduplicated.values(),
        key=lambda item: (
            item["state"] != "confirmed",
            item.get("_position", 10_000),
            -item.get("_match_length", 0),
            -item["confidence"],
        ),
    )[:12]
    primary = next((item for item in result if item["state"] == "confirmed"), None)
    if primary:
        primary["is_primary"] = True
    for item in result:
        item.pop("_position", None)
        item.pop("_match_length", None)
    return result


def _dedupe_key(
    server_number: int,
    reporter_id: str | None,
    message: str,
    subjects: Sequence[dict] | None = None,
    target_id: str | None = None,
) -> str:
    signatures = []
    for subject in subjects or ():
        if subject.get("kind") == "player":
            signatures.append(f"player:{subject.get('player_id') or ''}")
        elif subject.get("kind") == "squad":
            signatures.append(
                "squad:"
                f"{_normalize_message(str(subject.get('team') or ''))}:"
                f"{_normalize_message(str(subject.get('squad_name') or ''))}"
            )
    if not signatures and target_id:
        signatures.append(f"player:{target_id}")
    signature = ",".join(sorted(set(signatures)))
    raw = (
        f"{server_number}:{reporter_id or ''}:{_normalize_message(message)}:"
        f"{signature}"
    )
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


def _legacy_player_target(
    remainder: str, current_players: Sequence[dict]
) -> tuple[dict | None, str]:
    """Keep the pre-context resolver contract while the feature is disabled."""

    normalized_remainder = _normalize_message(remainder)
    matches = []
    for player in current_players:
        name = str(player.get("name") or player.get("player_name") or "").strip()
        normalized_name = _normalize_message(name)
        if normalized_name and (
            normalized_remainder == normalized_name
            or normalized_remainder.startswith(normalized_name + " ")
        ):
            matches.append((len(normalized_name), name, player))
    if not matches:
        return None, remainder
    matches.sort(key=lambda item: item[0], reverse=True)
    longest_length = matches[0][0]
    longest = [item for item in matches if item[0] == longest_length]
    if len(longest) != 1:
        return None, remainder
    _, name, player = longest[0]
    reason = remainder[len(name) :].strip(" :-\t") or remainder
    return player, reason


def parse_chat_report(
    message: str,
    trigger_words: Iterable[str] = DEFAULT_TRIGGER_WORDS,
    current_players: Sequence[dict] | None = None,
    current_squads: Sequence[dict] | None = None,
    reporter_context: dict | None = None,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    context_mode: str = "enabled",
) -> dict | None:
    """Resolve unique players/squads and expose fuzzy matches as suggestions."""

    trigger, match = _trigger_match(message, trigger_words)
    if not match:
        return None
    remainder = message[match.end() :].strip(" :-\t")
    if not remainder:
        remainder = "Admin assistance requested"

    if context_mode == "disabled":
        target, reason = _legacy_player_target(remainder, current_players or ())
        return {
            "trigger": trigger,
            "target_id": str(target.get("player_id") or "") or None if target else None,
            "target_name": (
                str(target.get("name") or target.get("player_name") or "") or None
                if target
                else None
            ),
            "subjects": [],
            "reason": reason[:4000],
            "raw_message": message[:4000],
        }

    reason = remainder
    subjects = _resolve_subjects(
        remainder,
        current_players=current_players or (),
        current_squads=current_squads or (),
        reporter_context=reporter_context or {},
        fuzzy_threshold=max(0.0, min(float(fuzzy_threshold), 1.0)),
        shadow=context_mode == "shadow",
    )
    primary = next(
        (
            subject
            for subject in subjects
            if subject["state"] == "confirmed" and subject["is_primary"]
        ),
        None,
    )
    target_id = None
    target_name = None
    if primary:
        target_id = primary.get("player_id") or primary.get("leader_player_id")
        target_name = (
            primary.get("display_name")
            if primary["kind"] == "player"
            else primary.get("leader_name")
        )
        normalized_remainder = _normalize_message(remainder)
        normalized_target = _normalize_message(primary["display_name"])
        if normalized_remainder.startswith(normalized_target + " "):
            reason = (
                remainder[len(primary["display_name"]) :].strip(" :-\t") or remainder
            )

    return {
        "trigger": trigger,
        "target_id": target_id,
        "target_name": target_name,
        "subjects": subjects,
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


def _subject_from_payload(payload: dict, *, actor: str | None = None):
    kind = str(payload.get("kind") or "").strip().lower()
    state = str(payload.get("state") or "suggested").strip().lower()
    if kind not in SUBJECT_KINDS or state not in SUBJECT_STATES:
        raise ValueError("Unsupported incident subject kind or state")
    display_name = str(
        payload.get("display_name")
        or payload.get("squad_name")
        or payload.get("player_name")
        or ""
    ).strip()
    player_id = str(payload.get("player_id") or "").strip() or None
    if not display_name or (kind == "player" and not player_id):
        raise ValueError("Incident player subjects require a name and player_id")
    return AdminIncidentSubject(
        kind=kind,
        state=state,
        is_primary=bool(payload.get("is_primary")) and state == "confirmed",
        display_name=display_name[:255],
        player_id=player_id[:100] if player_id else None,
        team=str(payload.get("team") or "")[:100] or None,
        squad_name=str(payload.get("squad_name") or "")[:100] or None,
        squad_id=str(payload.get("squad_id") or "")[:100] or None,
        squad_type=str(payload.get("squad_type") or "")[:32] or None,
        role=str(payload.get("role") or "")[:100] or None,
        leader_player_id=str(payload.get("leader_player_id") or "")[:100] or None,
        leader_name=str(payload.get("leader_name") or "")[:255] or None,
        confidence=(
            max(0.0, min(float(payload["confidence"]), 1.0))
            if payload.get("confidence") is not None
            else None
        ),
        match_method=str(payload.get("match_method") or "")[:64] or None,
        matched_text=str(payload.get("matched_text") or "")[:255] or None,
        parser_version=str(payload.get("parser_version") or "")[:32] or None,
        snapshot=dict(payload.get("snapshot") or {}),
        confirmed_by=actor if state == "confirmed" else None,
    )


def _sync_primary_target(incident: AdminIncident) -> None:
    confirmed = [
        subject for subject in incident.subjects if subject.state == "confirmed"
    ]
    primary = next((subject for subject in confirmed if subject.is_primary), None)
    if primary is None and confirmed:
        primary = confirmed[0]
        primary.is_primary = True
    for subject in incident.subjects:
        if subject is not primary:
            subject.is_primary = False
    if primary is None:
        incident.target_id = None
        incident.target_name = None
    elif primary.kind == "player":
        incident.target_id = primary.player_id
        incident.target_name = primary.display_name
    else:
        incident.target_id = primary.leader_player_id
        incident.target_name = primary.leader_name


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
    reporter_context: dict | None = None,
    subjects: Sequence[dict] | None = None,
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
        dedupe_key = _dedupe_key(
            server_number,
            reporter_id,
            raw_message,
            subjects=subjects,
            target_id=target_id,
        )

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
            reporter_context=dict(reporter_context or {}),
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
        subject_payloads = list(subjects or ())
        if not subject_payloads and target_id and target_name:
            subject_payloads.append(
                {
                    "kind": "player",
                    "state": "confirmed",
                    "is_primary": True,
                    "display_name": target_name,
                    "player_id": target_id,
                    "confidence": 1.0,
                    "match_method": "legacy_target",
                    "parser_version": "legacy",
                    "snapshot": {},
                }
            )
        incident.subjects.extend(
            _subject_from_payload(payload, actor=actor) for payload in subject_payloads
        )
        _sync_primary_target(incident)
        sess.add(incident)
        sess.flush()
        result = incident.to_dict(include_events=True)
    return result, True


def create_incident_from_chat(
    log: dict,
    *,
    current_players: Sequence[dict] | None = None,
    current_squads: Sequence[dict] | None = None,
    trigger_words: Iterable[str] = DEFAULT_TRIGGER_WORDS,
) -> tuple[dict, bool] | None:
    players = list(current_players or ())
    reporter_id = str(log.get("player_id_1") or "") or None
    reporter = next(
        (player for player in players if str(player.get("player_id")) == reporter_id),
        None,
    )
    reporter_context = player_snapshot(reporter)
    reporter_context["online"] = reporter is not None
    context_mode = os.getenv("MOBILE_CONTEXT_V2", "disabled").strip().lower()
    if context_mode in {"1", "true", "on", "enabled"}:
        context_mode = "enabled"
    elif context_mode != "shadow":
        context_mode = "disabled"
    parsed = parse_chat_report(
        str(log.get("sub_content") or ""),
        trigger_words=trigger_words,
        current_players=current_players,
        current_squads=current_squads if context_mode != "disabled" else (),
        reporter_context=reporter_context,
        fuzzy_threshold=_mobile_context_fuzzy_threshold(),
        context_mode=context_mode,
    )
    if not parsed:
        return None
    return create_incident(
        server_number=int(get_server_number()),
        source="chat",
        reason=parsed["reason"],
        raw_message=parsed["raw_message"],
        actor="system:chat",
        reporter_id=reporter_id,
        reporter_name=str(log.get("player_name_1") or "") or None,
        target_id=parsed["target_id"],
        target_name=parsed["target_name"],
        reporter_context=reporter_context if context_mode != "disabled" else {},
        subjects=parsed["subjects"] if context_mode != "disabled" else None,
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
            handover_note = str(payload.get("handover_note") or "").strip()
            payload = {
                "assigned_to": incident.assigned_to,
                "handover_note": handover_note[:2000] if handover_note else None,
            }
        elif operation == "link_target":
            target_id = str(payload.get("target_id") or "").strip()
            target_name = str(payload.get("target_name") or "").strip()
            if not target_id or not target_name:
                raise ValueError("target_id and target_name are required")
            incident.target_id = target_id[:100]
            incident.target_name = target_name[:255]
            existing_subject = next(
                (
                    subject
                    for subject in incident.subjects
                    if subject.kind == "player" and subject.player_id == target_id
                ),
                None,
            )
            if existing_subject:
                existing_subject.state = "confirmed"
                existing_subject.confirmed_by = actor
                existing_subject.display_name = target_name[:255]
                existing_subject.is_primary = True
            else:
                incident.subjects.append(
                    _subject_from_payload(
                        {
                            "kind": "player",
                            "state": "confirmed",
                            "is_primary": True,
                            "display_name": target_name,
                            "player_id": target_id,
                            "confidence": 1.0,
                            "match_method": "manual",
                            "parser_version": PARSER_VERSION,
                            "snapshot": {},
                        },
                        actor=actor,
                    )
                )
            _sync_primary_target(incident)
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


def mutate_incident_subject(
    incident_id: str,
    *,
    actor: str,
    expected_revision: int,
    operation: str,
    payload: dict,
    subject_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    if not idempotency_key or len(idempotency_key) > 64:
        raise ValueError("A valid Idempotency-Key header is required")
    with enter_session() as sess:
        existing_event = sess.execute(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if existing_event:
            if existing_event.incident_id != incident_id:
                raise IncidentConflict("Idempotency key belongs to another incident")
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

        subject = None
        if operation == "add":
            manual_payload = {
                **payload,
                "state": "confirmed",
                "confidence": 1.0,
                "match_method": "manual",
                "parser_version": PARSER_VERSION,
            }
            subject = _subject_from_payload(manual_payload, actor=actor)
            duplicate = next(
                (
                    item
                    for item in incident.subjects
                    if _subject_key(item.to_dict()) == _subject_key(subject.to_dict())
                ),
                None,
            )
            if duplicate:
                subject = duplicate
                subject.state = "confirmed"
                subject.confirmed_by = actor
            else:
                incident.subjects.append(subject)
            event_type = "subject_added"
        else:
            subject = next(
                (item for item in incident.subjects if item.id == subject_id), None
            )
            if not subject:
                raise IncidentNotFound("Incident subject not found")
            if operation == "confirm":
                subject.state = "confirmed"
                subject.confirmed_by = actor
                event_type = "subject_confirmed"
            elif operation == "reject":
                subject.state = "rejected"
                subject.is_primary = False
                subject.confirmed_by = None
                event_type = "subject_rejected"
            elif operation == "set_primary":
                if subject.state != "confirmed":
                    raise InvalidIncidentTransition(
                        "Only confirmed subjects can become primary"
                    )
                subject.is_primary = True
                event_type = "subject_primary"
            else:
                raise ValueError("Unsupported incident subject operation")

        _sync_primary_target(incident)
        incident.revision += 1
        incident.updated_at = _utcnow()
        subject.updated_at = incident.updated_at
        event = _event(
            actor,
            event_type,
            {
                "subject_id": subject.id,
                "kind": subject.kind,
                "state": subject.state,
                "is_primary": subject.is_primary,
                "match_method": subject.match_method,
                "confidence": subject.confidence,
            },
        )
        event.idempotency_key = idempotency_key
        incident.events.append(event)
        sess.flush()
        return incident.to_dict(include_events=True)


def confirmed_action_subject(
    incident: dict, *, player_id: str | None, subject_id: str | None = None
) -> dict:
    player_id = str(player_id or "").strip()
    subjects = incident.get("subjects") or []
    if not player_id and incident.get("target_id"):
        player_id = str(incident["target_id"])
    if not player_id:
        raise ValueError("Select a confirmed player before running an action")
    for subject in subjects:
        if subject.get("state") != "confirmed":
            continue
        if subject_id and subject.get("id") != subject_id:
            continue
        if subject.get("kind") == "player" and subject.get("player_id") == player_id:
            return subject
        if subject.get("kind") == "squad":
            members = (subject.get("snapshot") or {}).get("players") or []
            if any(str(member.get("player_id")) == player_id for member in members):
                return subject
    if not subjects and player_id == str(incident.get("target_id") or ""):
        return {
            "id": None,
            "kind": "player",
            "state": "confirmed",
            "player_id": player_id,
            "display_name": incident.get("target_name"),
        }
    raise ValueError("Actions require a player from a confirmed incident subject")


def reserve_incident_action(
    incident_id: str,
    *,
    actor: str,
    action: str,
    arguments: dict,
    idempotency_key: str,
    confirm_subject_id: str | None = None,
    validate_action_subject: bool = False,
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
        if incident.status not in {"new", "claimed"}:
            raise InvalidIncidentTransition(
                "Only open incidents can receive player actions"
            )
        if incident.assigned_to and incident.assigned_to != actor:
            raise IncidentConflict("Incident is already claimed by another admin")

        player_id = str(arguments.get("player_id") or "").strip()
        subject_id = str(arguments.get("subject_id") or "").strip() or None
        if action == "disband_squad":
            subject = next(
                (item for item in incident.subjects if item.id == subject_id),
                None,
            )
            if not subject:
                raise IncidentNotFound("Incident subject not found")
            if subject.kind != "squad" or subject.state != "confirmed":
                raise InvalidIncidentTransition(
                    "Only a confirmed squad can be disbanded"
                )
        elif confirm_subject_id:
            subject = next(
                (item for item in incident.subjects if item.id == confirm_subject_id),
                None,
            )
            if not subject:
                raise IncidentNotFound("Incident subject not found")
            if subject.kind != "player" or subject.state != "suggested":
                raise InvalidIncidentTransition(
                    "Only a suggested player can be confirmed during an action"
                )
            if subject.player_id != player_id or subject_id != subject.id:
                raise ValueError("Action target does not match the selected suggestion")
            subject.state = "confirmed"
            subject.confirmed_by = actor
            subject.is_primary = True
            _sync_primary_target(incident)
            incident.events.append(
                _event(
                    actor,
                    "subject_confirmed",
                    {
                        "subject_id": subject.id,
                        "kind": subject.kind,
                        "state": subject.state,
                        "is_primary": subject.is_primary,
                        "match_method": subject.match_method,
                        "confidence": subject.confidence,
                        "via": "action",
                    },
                )
            )
        elif validate_action_subject:
            confirmed_action_subject(
                incident.to_dict(include_events=False),
                player_id=player_id,
                subject_id=subject_id,
            )

        if incident.status == "new":
            incident.status = "claimed"
            incident.assigned_to = actor
            incident.events.append(
                _event(actor, "claim", {"via": "action", "action": action})
            )
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
