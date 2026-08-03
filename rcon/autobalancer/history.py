from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Any, Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from rcon.models import (
    AutobalanceDecision,
    AutobalancePlayerRoleStats,
    AutobalanceRoundAnalysis,
    AutobalanceSnapshot,
    LogLine,
    Maps,
    PlayerID,
    PlayerStats,
    enter_session,
)

from .models import BalanceSnapshot, PlayerSnapshot, SkillRating
from .planner import build_strategy_plans
from .rating import HistoricalSample


def load_history(
    player_ids: list[str],
    server_numbers: list[int],
    now: datetime | None = None,
    map_limit: int = 20,
) -> dict[str, list[HistoricalSample]]:
    if not player_ids:
        return {}
    now = now or datetime.utcnow()
    legacy_query = (
        select(PlayerID.player_id, PlayerStats, Maps.id, Maps.start)
        .join(PlayerStats, PlayerStats.player_id_id == PlayerID.id)
        .join(Maps, Maps.id == PlayerStats.map_id)
        .where(
            PlayerID.player_id.in_(player_ids),
            Maps.end.is_not(None),
            Maps.start >= now - timedelta(days=90),
            PlayerStats.time_seconds >= 10 * 60,
        )
        .order_by(PlayerID.player_id, Maps.start.desc())
    )
    if server_numbers:
        legacy_query = legacy_query.where(Maps.server_number.in_(server_numbers))
    result: dict[str, list[HistoricalSample]] = defaultdict(list)
    with enter_session() as session:
        exact_query = (
            select(AutobalancePlayerRoleStats)
            .where(
                AutobalancePlayerRoleStats.player_id.in_(player_ids),
                AutobalancePlayerRoleStats.last_seen >= now - timedelta(days=90),
            )
            .order_by(
                AutobalancePlayerRoleStats.player_id,
                AutobalancePlayerRoleStats.last_seen.desc(),
            )
        )
        if server_numbers:
            exact_query = exact_query.where(
                AutobalancePlayerRoleStats.server_number.in_(server_numbers)
            )
        exact_rows = session.scalars(exact_query).all()
        exact_by_player_round: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for row in exact_rows:
            exact_by_player_round[(row.player_id, row.round_id)].append(row)
        exact_rounds: dict[str, int] = defaultdict(int)
        for (player_id, round_id), rows in exact_by_player_round.items():
            if exact_rounds[player_id] >= map_limit:
                continue
            if sum(max(0, row.time_seconds) for row in rows) < 10 * 60:
                continue
            exact_rounds[player_id] += 1
            for row in rows:
                result[player_id].append(
                    HistoricalSample(
                        time_seconds=row.time_seconds,
                        kills=row.kills,
                        deaths=row.deaths,
                        teamkills=row.teamkills,
                        combat=row.combat,
                        offense=row.offense,
                        defense=row.defense,
                        support=row.support,
                        role_family=row.role_family,
                        map_key=round_id,
                        observed_at=row.last_seen,
                        exact=True,
                    )
                )

        legacy_counts: dict[str, int] = defaultdict(int)
        for player_id, stats, map_id, map_start in session.execute(legacy_query):
            if legacy_counts[player_id] >= map_limit:
                continue
            legacy_counts[player_id] += 1
            result[player_id].append(
                HistoricalSample(
                    time_seconds=stats.time_seconds,
                    kills=stats.kills,
                    deaths=stats.deaths,
                    teamkills=stats.teamkills,
                    combat=stats.combat,
                    offense=stats.offense,
                    defense=stats.defense,
                    support=stats.support,
                    role_family="legacy",
                    map_key=f"map:{map_id}",
                    observed_at=map_start,
                    exact=False,
                )
            )
    return dict(result)


TEAM_CHANGE = re.compile(r"\((None|Allies|Axis)\s*>\s*(None|Allies|Axis)\)")
TEAM_IN_PLAYER = re.compile(r"\((Allies|Axis)/[^)]*\)")
ANALYSIS_VERSION = "history-v3-role-aware"


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _round_id(game: Maps) -> str:
    started = game.start
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return f"{int(started.timestamp())}:{game.map_name}"


def _normalize_name(value: str | None) -> str | None:
    if not value:
        return None
    return " ".join(value.casefold().split())


def _config_values(
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    stable_difference_seconds: int,
    connection_grace_seconds: int = 120,
    max_switches_per_incident: int = 3,
    skill_gap_soft_limit: float = 8.0,
    skill_gap_hard_warning: float = 12.0,
    skill_gap_min_improvement: float = 2.5,
) -> dict[str, int | float]:
    return {
        "target_difference": int(target_difference),
        "minimum_players": int(minimum_players),
        "round_start_protection_seconds": int(round_start_protection_seconds),
        "round_end_protection_seconds": int(round_end_protection_seconds),
        "stable_difference_seconds": int(stable_difference_seconds),
        "connection_grace_seconds": int(connection_grace_seconds),
        "max_switches_per_incident": int(max_switches_per_incident),
        "skill_gap_soft_limit": float(skill_gap_soft_limit),
        "skill_gap_hard_warning": float(skill_gap_hard_warning),
        "skill_gap_min_improvement": float(skill_gap_min_improvement),
    }


def _config_hash(values: dict[str, int | float]) -> str:
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _event_record(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return dict(event)
    values = tuple(event)
    if len(values) == 4:
        event_time, player_name, action, content = values
        return {
            "event_time": event_time,
            "player1_name": player_name,
            "action": action,
            "content": content,
            "raw": content,
        }
    raise ValueError("Unsupported historical event shape")


def _evaluate_timeline(
    start: datetime,
    end: datetime,
    points: list[dict[str, Any]],
    quality: dict[str, Any],
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    stable_difference_seconds: int,
    sample_seconds: int,
) -> dict[str, Any]:
    eligible_start = start + timedelta(seconds=round_start_protection_seconds)
    eligible_end = end - timedelta(seconds=round_end_protection_seconds)

    def is_eligible(point: dict[str, Any]) -> bool:
        observed_at = datetime.fromisoformat(point["updated_at"])
        return (
            point.get("complete", True)
            and eligible_start <= observed_at <= eligible_end
            and sum(point["team_counts"].values()) >= minimum_players
        )

    eligible = [point for point in points if is_eligible(point)]
    unbalanced = [
        point for point in eligible if abs(point["team_difference"]) > target_difference
    ]

    longest_run = 0
    current_run = 0
    current_direction = 0
    incident_count = 0
    estimated_switches = 0
    incident_open = False
    for point in points:
        difference = point["team_difference"]
        direction = 1 if difference > 0 else -1 if difference < 0 else 0
        if (
            not is_eligible(point)
            or abs(difference) <= target_difference
            or (current_direction and direction != current_direction)
        ):
            current_run = 0
            incident_open = False
        if is_eligible(point) and abs(difference) > target_difference:
            current_direction = direction
            current_run += sample_seconds
            if current_run >= stable_difference_seconds and not incident_open:
                incident_count += 1
                estimated_switches += max(
                    1,
                    (abs(difference) - target_difference + 1) // 2,
                )
                incident_open = True
            longest_run = max(longest_run, current_run)
        elif abs(difference) <= target_difference:
            current_direction = 0

    measurable = bool(quality.get("reliable")) and bool(eligible)
    if not measurable:
        status = "not_measurable"
    elif incident_count:
        status = "unbalanced"
    elif unbalanced:
        status = "transient"
    else:
        status = "balanced"

    absolute_differences = [abs(point["team_difference"]) for point in eligible]
    return {
        "status": status,
        "timeline": points,
        "quality": quality,
        "metrics": {
            "eligible_samples": len(eligible),
            "balanced_samples": len(eligible) - len(unbalanced),
            "balanced_ratio": (
                round((len(eligible) - len(unbalanced)) / len(eligible), 4)
                if measurable
                else None
            ),
            "unbalanced_seconds": len(unbalanced) * sample_seconds,
            "longest_unbalanced_seconds": longest_run,
            "maximum_difference": max(absolute_differences, default=None),
            "mean_absolute_difference": (
                round(mean(absolute_differences), 2)
                if measurable and absolute_differences
                else None
            ),
            "incident_count": incident_count,
            "estimated_switches": estimated_switches,
        },
    }


def reconstruct_round_timeline(
    start: datetime,
    end: datetime,
    events: Iterable[tuple[datetime, str | None, str, str]],
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    stable_difference_seconds: int,
    sample_seconds: int = 30,
) -> dict[str, Any]:
    """Reconstruct team counts from all available team-bearing log evidence."""
    start = _as_utc(start)
    end = _as_utc(end)
    ordered_events = sorted(
        [_event_record(event) for event in events],
        key=lambda event: _as_utc(event["event_time"]),
    )
    players: dict[str, str | None] = {}
    normalized_events: list[dict[str, Any]] = []
    team_switch_events = 0
    team_evidence_events = 0
    invalid_events = 0
    conflicts = 0

    def identity(player_id: str | None, player_name: str | None) -> str | None:
        normalized_name = _normalize_name(player_name)
        if normalized_name:
            return f"name:{normalized_name}"
        return f"id:{player_id}" if player_id else None

    for raw_event in ordered_events:
        event = dict(raw_event)
        event["event_time"] = _as_utc(event["event_time"])
        action = str(event.get("action") or "")
        event["action"] = action
        event["key1"] = identity(event.get("player1_id"), event.get("player1_name"))
        event["key2"] = identity(event.get("player2_id"), event.get("player2_name"))
        if action in {"CONNECTED", "DISCONNECTED"}:
            if not event["key1"]:
                invalid_events += 1
                continue
            normalized_events.append(event)
            continue
        if action == "TEAMSWITCH":
            match = TEAM_CHANGE.search(
                str(event.get("content") or event.get("raw") or "")
            )
            if not event["key1"] or not match:
                invalid_events += 1
                continue
            event["old_team"], event["new_team"] = match.groups()
            team_switch_events += 1
            team_evidence_events += 1
            normalized_events.append(event)
            continue
        if action in {"KILL", "TEAM KILL"}:
            teams = TEAM_IN_PLAYER.findall(str(event.get("raw") or ""))
            if not teams:
                invalid_events += 1
                continue
            event["team1"] = teams[0]
            event["team2"] = teams[1] if len(teams) > 1 else teams[0]
            team_evidence_events += 1
            normalized_events.append(event)
            continue
        if action.startswith("CHAT["):
            team_match = re.search(r"CHAT\[(Allies|Axis)\]", action)
            if not event["key1"] or not team_match:
                invalid_events += 1
                continue
            event["team1"] = team_match.group(1)
            team_evidence_events += 1
            normalized_events.append(event)

    points: list[dict[str, Any]] = []
    index = 0
    sample_time = start
    max_players = 0
    coverage_samples: list[float] = []

    def apply_team(key: str | None, team: str | None) -> None:
        nonlocal conflicts
        if not key or team not in {"Allies", "Axis"}:
            return
        current_team = players.get(key)
        if current_team and current_team != team:
            conflicts += 1
        players[key] = team

    while sample_time <= end:
        while (
            index < len(normalized_events)
            and normalized_events[index]["event_time"] <= sample_time
        ):
            event = normalized_events[index]
            action = event["action"]
            key1 = event.get("key1")
            if action == "CONNECTED":
                players.setdefault(key1, None)
            elif action == "DISCONNECTED":
                players.pop(key1, None)
            elif action == "TEAMSWITCH":
                old_team = event["old_team"]
                new_team = event["new_team"]
                current_team = players.get(key1)
                if old_team != "None" and current_team not in {None, old_team}:
                    conflicts += 1
                if new_team == "None":
                    players[key1] = None
                else:
                    apply_team(key1, new_team)
            elif action in {"KILL", "TEAM KILL"}:
                apply_team(key1, event.get("team1"))
                apply_team(event.get("key2"), event.get("team2"))
            elif action.startswith("CHAT["):
                apply_team(key1, event.get("team1"))
            index += 1

        allies = sum(team == "Allies" for team in players.values())
        axis = sum(team == "Axis" for team in players.values())
        unknown = sum(team is None for team in players.values())
        max_players = max(max_players, allies + axis)
        observed = allies + axis + unknown
        coverage = (allies + axis) / observed if observed else 0.0
        coverage_samples.append(coverage)
        points.append(
            {
                "updated_at": _utc_iso(sample_time),
                "team_counts": {"allies": allies, "axis": axis},
                "team_difference": allies - axis,
                "unknown_players": unknown,
                "known_team_share": round(coverage, 4),
                "complete": True,
            }
        )
        sample_time += timedelta(seconds=sample_seconds)

    anomaly_count = invalid_events + conflicts
    anomaly_rate = anomaly_count / max(1, len(ordered_events))
    mean_known_share = mean(coverage_samples) if coverage_samples else 0.0
    quality_score = max(
        0.0,
        min(1.0, max_players / max(1, minimum_players))
        * (1.0 - min(1.0, anomaly_rate))
        * mean_known_share,
    )
    reliable = (
        team_evidence_events >= 20
        and max_players >= minimum_players
        and anomaly_rate <= 0.1
        and mean_known_share >= 0.8
    )
    quality = {
        "source": "historical_logs",
        "level": (
            "high"
            if quality_score >= 0.85
            else "medium" if quality_score >= 0.6 else "low"
        ),
        "score": round(quality_score, 4),
        "reliable": reliable,
        "valid_events": len(normalized_events),
        "team_switch_events": team_switch_events,
        "team_evidence_events": team_evidence_events,
        "invalid_or_conflicting_events": anomaly_count,
        "anomaly_rate": round(anomaly_rate, 4),
        "mean_known_team_share": round(mean_known_share, 4),
        "maximum_observed_players": max_players,
    }
    return _evaluate_timeline(
        start,
        end,
        points,
        quality,
        target_difference=target_difference,
        minimum_players=minimum_players,
        round_start_protection_seconds=round_start_protection_seconds,
        round_end_protection_seconds=round_end_protection_seconds,
        stable_difference_seconds=stable_difference_seconds,
        sample_seconds=sample_seconds,
    )


def _stored_snapshot_rating(payload: dict[str, Any]) -> dict[str, Any]:
    stored_rating = payload.get("rating")
    if isinstance(stored_rating, dict):
        return stored_rating
    if isinstance(stored_rating, (int, float)) and not isinstance(stored_rating, bool):
        confidence = payload.get("rating_confidence")
        try:
            confidence = max(0.0, min(0.4, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0
        value = float(stored_rating)
        return {
            "version": "legacy",
            "value": value,
            "raw_value": value,
            "confidence": confidence,
            "role_family": "legacy",
            "history_source": "legacy_snapshot",
        }
    return {}


def _snapshot_player(payload: dict[str, Any]) -> PlayerSnapshot | None:
    player_id = str(payload.get("player_id") or "")
    team = str(payload.get("team") or "").lower()
    if not player_id or team not in {"allies", "axis"}:
        return None
    stored_rating = _stored_snapshot_rating(payload)
    rating_fields = {
        field: stored_rating[field]
        for field in SkillRating.__dataclass_fields__
        if field in stored_rating
    }
    return PlayerSnapshot(
        player_id=player_id,
        name=str(payload.get("name") or player_id),
        team=team,
        role=str(payload.get("role") or ""),
        level=payload.get("level"),
        unit_id=payload.get("unit_id"),
        unit_name=payload.get("unit_name"),
        unit_type=payload.get("unit_type"),
        unit_size=int(payload.get("unit_size") or 0),
        is_leader=bool(payload.get("is_leader")),
        connected_seconds=int(payload.get("connected_seconds") or 0),
        squad_seconds=int(payload.get("squad_seconds") or 0),
        map_playtime_seconds=int(payload.get("map_playtime_seconds") or 0),
        kills=int(payload.get("kills") or 0),
        deaths=int(payload.get("deaths") or 0),
        teamkills=int(payload.get("teamkills") or 0),
        combat=int(payload.get("combat") or 0),
        offense=int(payload.get("offense") or 0),
        defense=int(payload.get("defense") or 0),
        support=int(payload.get("support") or 0),
        rating=SkillRating(**rating_fields),
    )


def _snapshot_candidate_what_if(
    start: datetime,
    end: datetime,
    rows: list[AutobalanceSnapshot],
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    connection_grace_seconds: int,
    max_switches_per_incident: int,
    skill_gap_soft_limit: float,
    skill_gap_hard_warning: float,
    skill_gap_min_improvement: float,
) -> dict[str, Any] | None:
    eligible_start = _as_utc(start) + timedelta(seconds=round_start_protection_seconds)
    eligible_end = _as_utc(end) - timedelta(seconds=round_end_protection_seconds)
    eligible = [
        row
        for row in rows
        if row.counts_match
        and row.fail_count == 0
        and row.stable_map
        and row.players
        and row.allies_count + row.axis_count >= minimum_players
        and abs(row.allies_count - row.axis_count) > target_difference
        and eligible_start <= _as_utc(row.captured_at) <= eligible_end
    ]
    if not eligible:
        return None
    row = max(
        eligible,
        key=lambda item: (
            abs(item.allies_count - item.axis_count),
            -_as_utc(item.captured_at).timestamp(),
        ),
    )
    players = [
        player
        for player in (_snapshot_player(payload) for payload in row.players)
        if player is not None
    ]
    snapshot = BalanceSnapshot(
        round_id=row.round_id,
        captured_at=_as_utc(row.captured_at),
        map_name=row.map_name,
        map_elapsed_seconds=row.map_elapsed_seconds,
        time_remaining_seconds=row.time_remaining_seconds,
        allies_count=row.allies_count,
        axis_count=row.axis_count,
        players=players,
        fail_count=row.fail_count,
        counts_match=row.counts_match,
        stable_map=row.stable_map,
    )
    plans = build_strategy_plans(
        snapshot,
        target_difference=target_difference,
        connection_grace_seconds=connection_grace_seconds,
        max_switches=max_switches_per_incident,
        skill_gap_soft_limit=skill_gap_soft_limit,
        skill_gap_hard_warning=skill_gap_hard_warning,
        skill_gap_min_improvement=skill_gap_min_improvement,
    )
    return {
        "captured_at": _utc_iso(row.captured_at),
        "allies_count": row.allies_count,
        "axis_count": row.axis_count,
        "rating_model_version": row.rating_model_version or "legacy",
        "strategies": {
            name: plan.public_dict() if plan is not None else None
            for name, plan in plans.items()
        },
        "limitations": (
            "Exakter Snapshot; historische Freiwilligkeit, aktive Vormerkungen "
            "und eine eventuell bereits laufende Drei-Karten-Schutzfrist sind "
            "nicht rückwirkend ableitbar."
        ),
    }


def analyze_snapshot_timeline(
    start: datetime,
    end: datetime,
    snapshots: Iterable[AutobalanceSnapshot],
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    stable_difference_seconds: int,
    connection_grace_seconds: int = 120,
    max_switches_per_incident: int = 3,
    skill_gap_soft_limit: float = 8.0,
    skill_gap_hard_warning: float = 12.0,
    skill_gap_min_improvement: float = 2.5,
) -> dict[str, Any]:
    start = _as_utc(start)
    end = _as_utc(end)
    rows = list(snapshots)
    intervals = [
        max(
            1,
            int(
                (
                    _as_utc(current.captured_at) - _as_utc(previous.captured_at)
                ).total_seconds()
            ),
        )
        for previous, current in zip(rows, rows[1:])
    ]
    sample_seconds = int(sorted(intervals)[len(intervals) // 2]) if intervals else 30
    complete_count = sum(
        row.counts_match and row.fail_count == 0 and row.stable_map for row in rows
    )
    completeness = complete_count / len(rows) if rows else 0.0
    points = [
        {
            "updated_at": _utc_iso(row.captured_at),
            "team_counts": {
                "allies": row.allies_count,
                "axis": row.axis_count,
            },
            "team_difference": row.allies_count - row.axis_count,
            "unknown_players": 0,
            "known_team_share": 1.0,
            "complete": bool(
                row.counts_match and row.fail_count == 0 and row.stable_map
            ),
        }
        for row in rows
    ]
    quality = {
        "source": "live_snapshots",
        "level": "exact" if completeness >= 0.95 else "high",
        "score": round(completeness, 4),
        "reliable": len(rows) >= 4 and completeness >= 0.8,
        "valid_events": len(rows),
        "team_switch_events": 0,
        "team_evidence_events": len(rows),
        "invalid_or_conflicting_events": len(rows) - complete_count,
        "anomaly_rate": round(1.0 - completeness, 4),
        "mean_known_team_share": 1.0,
        "maximum_observed_players": max(
            (row.allies_count + row.axis_count for row in rows), default=0
        ),
        "roster_snapshots": sum(bool(row.players) for row in rows),
    }
    result = _evaluate_timeline(
        start,
        end,
        points,
        quality,
        target_difference=target_difference,
        minimum_players=minimum_players,
        round_start_protection_seconds=round_start_protection_seconds,
        round_end_protection_seconds=round_end_protection_seconds,
        stable_difference_seconds=stable_difference_seconds,
        sample_seconds=sample_seconds,
    )
    result["candidate_what_if"] = _snapshot_candidate_what_if(
        start,
        end,
        rows,
        target_difference=target_difference,
        minimum_players=minimum_players,
        round_start_protection_seconds=round_start_protection_seconds,
        round_end_protection_seconds=round_end_protection_seconds,
        connection_grace_seconds=connection_grace_seconds,
        max_switches_per_incident=max_switches_per_incident,
        skill_gap_soft_limit=skill_gap_soft_limit,
        skill_gap_hard_warning=skill_gap_hard_warning,
        skill_gap_min_improvement=skill_gap_min_improvement,
    )
    return result


def reanalyze_timeline(
    analysis: dict[str, Any],
    *,
    target_difference: int,
    minimum_players: int,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    stable_difference_seconds: int,
    connection_grace_seconds: int = 120,
    max_switches_per_incident: int = 3,
    skill_gap_soft_limit: float = 8.0,
    skill_gap_hard_warning: float = 12.0,
    skill_gap_min_improvement: float = 2.5,
) -> dict[str, Any]:
    round_data = analysis["round"]
    points = analysis.get("timeline") or []
    if len(points) >= 2:
        sample_seconds = max(
            1,
            int(
                (
                    datetime.fromisoformat(points[1]["updated_at"])
                    - datetime.fromisoformat(points[0]["updated_at"])
                ).total_seconds()
            ),
        )
    else:
        sample_seconds = 30
    result = _evaluate_timeline(
        _as_utc(datetime.fromisoformat(round_data["start"])),
        _as_utc(datetime.fromisoformat(round_data["end"])),
        points,
        analysis["quality"],
        target_difference=target_difference,
        minimum_players=minimum_players,
        round_start_protection_seconds=round_start_protection_seconds,
        round_end_protection_seconds=round_end_protection_seconds,
        stable_difference_seconds=stable_difference_seconds,
        sample_seconds=sample_seconds,
    )
    result["round"] = round_data
    result["candidate_what_if"] = analysis.get("candidate_what_if")
    return result


def summarize_round_analyses(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(analysis["status"] for analysis in analyses)
    quality_levels = Counter(
        analysis.get("quality", {}).get("level", "low") for analysis in analyses
    )
    measurable = [
        analysis for analysis in analyses if analysis["status"] != "not_measurable"
    ]
    eligible_samples = sum(
        analysis["metrics"].get("eligible_samples", 0) for analysis in measurable
    )
    balanced_samples = sum(
        analysis["metrics"].get("balanced_samples", 0) for analysis in measurable
    )
    incidents = sum(
        analysis["metrics"].get("incident_count", 0) for analysis in measurable
    )
    switches = sum(
        analysis["metrics"].get("estimated_switches", 0) for analysis in measurable
    )
    maximum_differences = [
        analysis["metrics"].get("maximum_difference")
        for analysis in measurable
        if analysis["metrics"].get("maximum_difference") is not None
    ]

    difference_buckets = {"0–2": 0, "3–4": 0, "5–6": 0, "7+": 0}
    for value in maximum_differences:
        if value <= 2:
            difference_buckets["0–2"] += 1
        elif value <= 4:
            difference_buckets["3–4"] += 1
        elif value <= 6:
            difference_buckets["5–6"] += 1
        else:
            difference_buckets["7+"] += 1

    weekly: dict[str, dict[str, Any]] = {}
    maps: dict[str, dict[str, Any]] = {}
    for analysis in measurable:
        started = datetime.fromisoformat(analysis["round"]["start"])
        week = (started - timedelta(days=started.weekday())).date().isoformat()
        week_row = weekly.setdefault(
            week,
            {"week": week, "rounds": 0, "eligible": 0, "balanced": 0, "incidents": 0},
        )
        map_name = analysis["round"].get("map_name") or "unknown"
        map_row = maps.setdefault(
            map_name,
            {
                "map_name": map_name,
                "rounds": 0,
                "eligible": 0,
                "balanced": 0,
                "incidents": 0,
            },
        )
        for row in (week_row, map_row):
            row["rounds"] += 1
            row["eligible"] += analysis["metrics"].get("eligible_samples", 0)
            row["balanced"] += analysis["metrics"].get("balanced_samples", 0)
            row["incidents"] += analysis["metrics"].get("incident_count", 0)

    def finish(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for row in rows:
            result.append(
                {
                    **row,
                    "balanced_ratio": (
                        round(row["balanced"] / row["eligible"], 4)
                        if row["eligible"]
                        else None
                    ),
                }
            )
        return result

    return {
        "rounds_analyzed": len(analyses),
        "measurable_rounds": len(measurable),
        "coverage_ratio": (
            round(len(measurable) / len(analyses), 4) if analyses else 0.0
        ),
        "statuses": dict(statuses),
        "quality_levels": dict(quality_levels),
        "balanced_time_ratio": (
            round(balanced_samples / eligible_samples, 4) if eligible_samples else None
        ),
        "incident_count": incidents,
        "incidents_per_10_rounds": (
            round(incidents / len(measurable) * 10, 2) if measurable else None
        ),
        "estimated_switches": switches,
        "switches_per_round": (
            round(switches / len(measurable), 2) if measurable else None
        ),
        "maximum_difference": max(maximum_differences, default=None),
        "difference_distribution": [
            {"bucket": bucket, "rounds": count}
            for bucket, count in difference_buckets.items()
        ],
        "weekly": sorted(finish(weekly.values()), key=lambda row: row["week"]),
        "maps": sorted(
            finish(maps.values()),
            key=lambda row: (-row["rounds"], row["map_name"]),
        )[:12],
    }


def summarize_rating_quality(
    games: Iterable[Any],
    snapshots: Iterable[AutobalanceSnapshot],
    decisions: Iterable[AutobalanceDecision],
    *,
    round_start_protection_seconds: int,
    round_end_protection_seconds: int,
    minimum_players: int = 40,
) -> dict[str, Any]:
    """Summarize only exact snapshot evidence; legacy logs never imply skill data."""
    games = list(games)
    snapshots = list(snapshots)
    decisions = list(decisions)
    games_by_round = {_round_id(game): game for game in games}
    expected_by_round: dict[str, int] = {}
    valid_snapshots = []
    valid_by_round: Counter[str] = Counter()
    confidences: list[float] = []
    role_observations: Counter[str] = Counter()
    role_confidences: dict[str, list[float]] = defaultdict(list)
    confidence_buckets: Counter[str] = Counter()
    model_versions: Counter[str] = Counter()
    well_attended_rounds = {
        snapshot.round_id
        for snapshot in snapshots
        if snapshot.allies_count + snapshot.axis_count >= minimum_players
    }
    for game in games:
        round_id = _round_id(game)
        if round_id not in well_attended_rounds:
            continue
        eligible_seconds = max(
            0,
            int((game.end - game.start).total_seconds())
            - round_start_protection_seconds
            - round_end_protection_seconds,
        )
        expected_by_round[round_id] = (eligible_seconds + 29) // 30
    expected_snapshots = sum(expected_by_round.values())
    for snapshot in snapshots:
        if snapshot.round_id not in expected_by_round:
            continue
        game = games_by_round.get(snapshot.round_id)
        if game is None:
            continue
        eligible_start = game.start + timedelta(seconds=round_start_protection_seconds)
        eligible_end = game.end - timedelta(seconds=round_end_protection_seconds)
        if not eligible_start <= snapshot.captured_at <= eligible_end:
            continue
        if not snapshot.counts_match or snapshot.fail_count or not snapshot.stable_map:
            continue
        valid_snapshots.append(snapshot)
        valid_by_round[snapshot.round_id] += 1
        model_versions[snapshot.rating_model_version or "legacy"] += 1
        for player in snapshot.players or []:
            rating = _stored_snapshot_rating(player)
            confidence = rating.get("confidence")
            if confidence is not None and rating.get("role_family") != "commander":
                confidence_value = max(0.0, min(1.0, float(confidence)))
                confidences.append(confidence_value)
            family = player.get("role_family") or rating.get("role_family") or "legacy"
            if family != "commander":
                role_observations[str(family)] += 1
                if confidence is not None:
                    role_confidences[str(family)].append(confidence_value)
                    bucket = (
                        "0–20 %"
                        if confidence_value < 0.2
                        else (
                            "20–40 %"
                            if confidence_value < 0.4
                            else (
                                "40–60 %"
                                if confidence_value < 0.6
                                else "60–80 %" if confidence_value < 0.8 else "80–100 %"
                            )
                        )
                    )
                    confidence_buckets[bucket] += 1

    strategy_rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"proposals": 0, "projected_gaps": []}
    )
    strategy_agreements = 0
    strategy_proposals = 0
    gap_guardrail_passes = 0
    gap_guardrail_total = 0
    for decision in decisions:
        reason = decision.reason or {}
        plans = reason.get("strategies") or {}
        candidate_ids = []
        for strategy, plan in plans.items():
            if not plan or not plan.get("candidates"):
                continue
            first = plan["candidates"][0]
            candidate_ids.append(first.get("player_id"))
            strategy_rows[strategy]["proposals"] += 1
            gap = plan.get("projected_rating_gap")
            if gap is not None:
                strategy_rows[strategy]["projected_gaps"].append(float(gap))
        if candidate_ids:
            strategy_proposals += 1
            strategy_agreements += len(set(candidate_ids)) == 1
        active_plan = reason.get("plan") or {}
        before = active_plan.get("rating_gap_before")
        after = active_plan.get("projected_rating_gap")
        if before is not None and after is not None:
            gap_guardrail_total += 1
            gap_guardrail_passes += float(after) <= float(before) + 2.0

    fully_captured_rounds = sum(
        expected > 0 and valid_by_round[round_id] / expected >= 0.95
        for round_id, expected in expected_by_round.items()
    )
    return {
        "expected_snapshots": expected_snapshots,
        "valid_snapshots": len(valid_snapshots),
        "snapshot_coverage": min(
            1.0,
            len(valid_snapshots) / expected_snapshots if expected_snapshots else 0.0,
        ),
        "well_attended_rounds": len(expected_by_round),
        "exact_rounds": fully_captured_rounds,
        "fully_captured_rounds": fully_captured_rounds,
        "median_rating_confidence": median(confidences) if confidences else None,
        "role_observations": dict(role_observations.most_common()),
        "role_confidence": [
            {
                "role_family": family,
                "observations": role_observations[family],
                "median_confidence": median(values),
            }
            for family, values in sorted(role_confidences.items())
        ],
        "confidence_distribution": [
            {"bucket": bucket, "observations": confidence_buckets[bucket]}
            for bucket in (
                "0–20 %",
                "20–40 %",
                "40–60 %",
                "60–80 %",
                "80–100 %",
            )
        ],
        "model_versions": dict(model_versions.most_common()),
        "latest_snapshot": _utc_iso(
            max((snapshot.captured_at for snapshot in valid_snapshots), default=None)
        ),
        "strategy_agreement_rate": (
            strategy_agreements / strategy_proposals if strategy_proposals else None
        ),
        "gap_guardrail_rate": (
            gap_guardrail_passes / gap_guardrail_total if gap_guardrail_total else None
        ),
        "strategies": [
            {
                "strategy": strategy,
                "proposals": values["proposals"],
                "average_projected_gap": (
                    mean(values["projected_gaps"]) if values["projected_gaps"] else None
                ),
            }
            for strategy, values in sorted(strategy_rows.items())
        ],
    }


class RoundHistoryRepository:
    def __init__(self, server_number: int):
        self.server_number = server_number

    def search(
        self,
        *,
        page: int = 1,
        limit: int = 12,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        page = max(1, page)
        limit = min(max(1, limit), 50)
        filters = [
            Maps.server_number == self.server_number,
            Maps.end.is_not(None),
        ]
        if search:
            filters.append(Maps.map_name.ilike(f"%{search.strip()}%"))
        if date_from:
            filters.append(Maps.start >= date_from)
        if date_to:
            filters.append(Maps.start < date_to)

        with enter_session() as session:
            total = session.scalar(select(func.count(Maps.id)).where(*filters)) or 0
            games = session.scalars(
                select(Maps)
                .where(*filters)
                .order_by(Maps.start.desc())
                .limit(limit)
                .offset((page - 1) * limit)
            ).all()
            round_ids = [_round_id(game) for game in games]
            proposal_counts = (
                dict(
                    session.execute(
                        select(
                            AutobalanceDecision.round_id,
                            func.count(AutobalanceDecision.id),
                        )
                        .where(
                            AutobalanceDecision.server_number == self.server_number,
                            AutobalanceDecision.round_id.in_(round_ids),
                        )
                        .group_by(AutobalanceDecision.round_id)
                    ).all()
                )
                if round_ids
                else {}
            )

            rounds = []
            for game in games:
                round_id = _round_id(game)
                result = game.result or {}
                rounds.append(
                    {
                        "map_id": game.id,
                        "round_id": round_id,
                        "map_name": game.map_name,
                        "start": _utc_iso(game.start),
                        "end": _utc_iso(game.end),
                        "duration_seconds": max(
                            0, int((game.end - game.start).total_seconds())
                        ),
                        "result": {
                            "allies": result.get("Allied"),
                            "axis": result.get("Axis"),
                        },
                        "shadow_proposals": proposal_counts.get(round_id, 0),
                    }
                )

        return {
            "page": page,
            "page_size": limit,
            "total": total,
            "rounds": rounds,
        }

    def analyze(
        self,
        map_id: int,
        *,
        target_difference: int,
        minimum_players: int,
        round_start_protection_seconds: int,
        round_end_protection_seconds: int,
        stable_difference_seconds: int,
        connection_grace_seconds: int = 120,
        max_switches_per_incident: int = 3,
        skill_gap_soft_limit: float = 8.0,
        skill_gap_hard_warning: float = 12.0,
        skill_gap_min_improvement: float = 2.5,
    ) -> dict[str, Any] | None:
        config = _config_values(
            target_difference=target_difference,
            minimum_players=minimum_players,
            round_start_protection_seconds=round_start_protection_seconds,
            round_end_protection_seconds=round_end_protection_seconds,
            stable_difference_seconds=stable_difference_seconds,
            connection_grace_seconds=connection_grace_seconds,
            max_switches_per_incident=max_switches_per_incident,
            skill_gap_soft_limit=skill_gap_soft_limit,
            skill_gap_hard_warning=skill_gap_hard_warning,
            skill_gap_min_improvement=skill_gap_min_improvement,
        )
        config_hash = _config_hash(config)
        with enter_session() as session:
            game = session.scalar(
                select(Maps).where(
                    Maps.id == map_id,
                    Maps.server_number == self.server_number,
                    Maps.end.is_not(None),
                )
            )
            if game is None:
                return None
            cached = session.scalar(
                select(AutobalanceRoundAnalysis).where(
                    AutobalanceRoundAnalysis.server_number == self.server_number,
                    AutobalanceRoundAnalysis.map_id == map_id,
                    AutobalanceRoundAnalysis.algorithm_version == ANALYSIS_VERSION,
                    AutobalanceRoundAnalysis.config_hash == config_hash,
                )
            )
            if cached is not None:
                return cached.analysis

            snapshots = session.scalars(
                select(AutobalanceSnapshot)
                .where(
                    AutobalanceSnapshot.server_number == self.server_number,
                    AutobalanceSnapshot.captured_at >= game.start,
                    AutobalanceSnapshot.captured_at <= game.end,
                )
                .order_by(AutobalanceSnapshot.captured_at)
            ).all()

            if len(snapshots) >= 4:
                analysis = analyze_snapshot_timeline(
                    game.start,
                    game.end,
                    snapshots,
                    **config,
                )
            else:
                player1 = aliased(PlayerID)
                player2 = aliased(PlayerID)
                event_rows = session.execute(
                    select(
                        LogLine.event_time,
                        LogLine.player1_name,
                        player1.player_id.label("player1_id"),
                        LogLine.player2_name,
                        player2.player_id.label("player2_id"),
                        LogLine.type,
                        LogLine.content,
                        LogLine.raw,
                    )
                    .outerjoin(player1, LogLine.player1_player_id == player1.id)
                    .outerjoin(player2, LogLine.player2_player_id == player2.id)
                    .where(
                        LogLine.server == str(self.server_number),
                        LogLine.event_time >= game.start,
                        LogLine.event_time <= game.end,
                        or_(
                            LogLine.type.in_(
                                [
                                    "TEAMSWITCH",
                                    "CONNECTED",
                                    "DISCONNECTED",
                                    "KILL",
                                    "TEAM KILL",
                                ]
                            ),
                            LogLine.type.like("CHAT[%"),
                        ),
                    )
                    .order_by(LogLine.event_time)
                ).all()
                events = [
                    {
                        "event_time": row.event_time,
                        "player1_name": row.player1_name,
                        "player1_id": row.player1_id,
                        "player2_name": row.player2_name,
                        "player2_id": row.player2_id,
                        "action": row.type,
                        "content": row.content,
                        "raw": row.raw,
                    }
                    for row in event_rows
                ]
                analysis = reconstruct_round_timeline(
                    game.start,
                    game.end,
                    events,
                    **{
                        key: config[key]
                        for key in (
                            "target_difference",
                            "minimum_players",
                            "round_start_protection_seconds",
                            "round_end_protection_seconds",
                            "stable_difference_seconds",
                        )
                    },
                )
            analysis["round"] = {
                "map_id": game.id,
                "round_id": _round_id(game),
                "map_name": game.map_name,
                "start": _utc_iso(game.start),
                "end": _utc_iso(game.end),
            }
            session.execute(
                insert(AutobalanceRoundAnalysis)
                .values(
                    server_number=self.server_number,
                    map_id=game.id,
                    algorithm_version=ANALYSIS_VERSION,
                    config_hash=config_hash,
                    analyzed_at=datetime.utcnow(),
                    source=analysis["quality"]["source"],
                    status=analysis["status"],
                    quality_score=analysis["quality"]["score"],
                    analysis=analysis,
                )
                .on_conflict_do_update(
                    constraint="unique_autobalance_round_analysis",
                    set_={
                        "analyzed_at": datetime.utcnow(),
                        "source": analysis["quality"]["source"],
                        "status": analysis["status"],
                        "quality_score": analysis["quality"]["score"],
                        "analysis": analysis,
                    },
                )
            )
            return analysis

    def dashboard(
        self,
        *,
        target_difference: int,
        minimum_players: int,
        round_start_protection_seconds: int,
        round_end_protection_seconds: int,
        stable_difference_seconds: int,
        connection_grace_seconds: int = 120,
        max_switches_per_incident: int = 3,
        skill_gap_soft_limit: float = 8.0,
        skill_gap_hard_warning: float = 12.0,
        skill_gap_min_improvement: float = 2.5,
        days: int = 90,
        search: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        days = min(max(7, int(days)), 730)
        limit = min(max(10, int(limit)), 250)
        date_from = datetime.utcnow() - timedelta(days=days)
        filters = [
            Maps.server_number == self.server_number,
            Maps.end.is_not(None),
            Maps.start >= date_from,
        ]
        if search:
            filters.append(Maps.map_name.ilike(f"%{search.strip()}%"))
        with enter_session() as session:
            games = session.execute(
                select(
                    Maps.id.label("id"),
                    Maps.start.label("start"),
                    Maps.end.label("end"),
                    Maps.server_number.label("server_number"),
                    Maps.map_name.label("map_name"),
                )
                .where(*filters)
                .order_by(Maps.start.desc())
                .limit(limit)
            ).all()
            map_ids = [game.id for game in games]

        base_config = _config_values(
            target_difference=target_difference,
            minimum_players=minimum_players,
            round_start_protection_seconds=round_start_protection_seconds,
            round_end_protection_seconds=round_end_protection_seconds,
            stable_difference_seconds=stable_difference_seconds,
            connection_grace_seconds=connection_grace_seconds,
            max_switches_per_incident=max_switches_per_incident,
            skill_gap_soft_limit=skill_gap_soft_limit,
            skill_gap_hard_warning=skill_gap_hard_warning,
            skill_gap_min_improvement=skill_gap_min_improvement,
        )
        config_hash = _config_hash(base_config)
        with enter_session() as session:
            cached_rows = session.execute(
                select(
                    AutobalanceRoundAnalysis.map_id,
                    AutobalanceRoundAnalysis.analysis,
                ).where(
                    AutobalanceRoundAnalysis.server_number == self.server_number,
                    AutobalanceRoundAnalysis.map_id.in_(map_ids),
                    AutobalanceRoundAnalysis.algorithm_version == ANALYSIS_VERSION,
                    AutobalanceRoundAnalysis.config_hash == config_hash,
                )
            ).all()
        analyses_by_map = {map_id: analysis for map_id, analysis in cached_rows}
        missing_map_ids = [
            map_id for map_id in map_ids if map_id not in analyses_by_map
        ]
        for map_id in missing_map_ids[:15]:
            analysis = self.analyze(map_id, **base_config)
            if analysis is not None:
                analyses_by_map[map_id] = analysis
        analyses = [
            analyses_by_map[map_id] for map_id in map_ids if map_id in analyses_by_map
        ]
        remaining = max(0, len(map_ids) - len(analyses))
        variants = [
            ("Schonend", {**base_config, "stable_difference_seconds": 60}),
            ("Aktueller Pilot", base_config),
            ("Reaktiv", {**base_config, "stable_difference_seconds": 30}),
            (
                "Streng",
                {
                    **base_config,
                    "target_difference": 1,
                    "stable_difference_seconds": 45,
                },
            ),
        ]
        what_if = []
        for label, variant_config in variants:
            variant_analyses = [
                reanalyze_timeline(analysis, **variant_config) for analysis in analyses
            ]
            what_if.append(
                {
                    "label": label,
                    "config": variant_config,
                    **summarize_round_analyses(variant_analyses),
                }
            )

        source_counts = Counter(
            analysis.get("quality", {}).get("source", "unknown")
            for analysis in analyses
        )
        round_ids = [_round_id(game) for game in games]
        with enter_session() as session:
            snapshots = (
                session.execute(
                    select(
                        AutobalanceSnapshot.round_id.label("round_id"),
                        AutobalanceSnapshot.captured_at.label("captured_at"),
                        AutobalanceSnapshot.allies_count.label("allies_count"),
                        AutobalanceSnapshot.axis_count.label("axis_count"),
                        AutobalanceSnapshot.counts_match.label("counts_match"),
                        AutobalanceSnapshot.fail_count.label("fail_count"),
                        AutobalanceSnapshot.stable_map.label("stable_map"),
                        AutobalanceSnapshot.rating_model_version.label(
                            "rating_model_version"
                        ),
                        AutobalanceSnapshot.players.label("players"),
                    )
                    .where(
                        AutobalanceSnapshot.server_number == self.server_number,
                        AutobalanceSnapshot.round_id.in_(round_ids),
                    )
                    .order_by(AutobalanceSnapshot.captured_at)
                ).all()
                if round_ids
                else []
            )
            decisions = (
                session.execute(
                    select(AutobalanceDecision.reason.label("reason")).where(
                        AutobalanceDecision.server_number == self.server_number,
                        AutobalanceDecision.round_id.in_(round_ids),
                        AutobalanceDecision.mode == "shadow",
                    )
                ).all()
                if round_ids
                else []
            )
        rating_quality = summarize_rating_quality(
            games,
            snapshots,
            decisions,
            round_start_protection_seconds=round_start_protection_seconds,
            round_end_protection_seconds=round_end_protection_seconds,
            minimum_players=minimum_players,
        )
        return {
            "generated_at": _utc_iso(datetime.utcnow()),
            "server_number": self.server_number,
            "filters": {
                "days": days,
                "search": search or "",
                "limit": limit,
            },
            "backfill": {
                "requested_rounds": len(map_ids),
                "analyzed_rounds": len(analyses),
                "remaining_rounds": remaining,
                "complete": remaining == 0,
            },
            "config": base_config,
            "source_counts": dict(source_counts),
            "summary": summarize_round_analyses(analyses),
            "what_if": what_if,
            "rating_quality": rating_quality,
        }
