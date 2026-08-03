from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import func, select

from rcon.models import (
    AutobalanceDecision,
    LogLine,
    Maps,
    PlayerID,
    PlayerStats,
    enter_session,
)

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
    query = (
        select(PlayerID.player_id, PlayerStats, Maps.start)
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
        query = query.where(Maps.server_number.in_(server_numbers))
    result: dict[str, list[HistoricalSample]] = defaultdict(list)
    with enter_session() as session:
        for player_id, stats, _ in session.execute(query):
            if len(result[player_id]) >= map_limit:
                continue
            result[player_id].append(
                HistoricalSample(
                    time_seconds=stats.time_seconds,
                    kills=stats.kills,
                    combat=stats.combat,
                    offense=stats.offense,
                    defense=stats.defense,
                    support=stats.support,
                )
            )
    return dict(result)


TEAM_CHANGE = re.compile(r"\((None|Allies|Axis)\s*>\s*(None|Allies|Axis)\)")


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
    """Reconstruct team counts from TEAMSWITCH events without inventing squad data."""
    start = _as_utc(start)
    end = _as_utc(end)
    ordered_events = sorted(
        [
            (_as_utc(event_time), player_name, action, content)
            for event_time, player_name, action, content in events
        ],
        key=lambda event: event[0],
    )
    players: dict[str, str] = {}
    normalized_events: list[tuple[datetime, str, str, str | None, str | None]] = []
    team_switch_events = 0
    invalid_events = 0
    conflicts = 0

    for event_time, player_name, action, content in ordered_events:
        if not player_name:
            invalid_events += 1
            continue
        if action in {"CONNECTED", "DISCONNECTED"}:
            normalized_events.append((event_time, player_name, action, None, None))
            continue
        match = TEAM_CHANGE.search(content or "")
        if action != "TEAMSWITCH" or not match:
            invalid_events += 1
            continue
        old_team, new_team = match.groups()
        team_switch_events += 1
        normalized_events.append(
            (event_time, player_name, action, old_team, new_team)
        )

    points: list[dict[str, Any]] = []
    index = 0
    sample_time = start
    max_players = 0
    while sample_time <= end:
        while (
            index < len(normalized_events)
            and normalized_events[index][0] <= sample_time
        ):
            _, player_name, action, old_team, new_team = normalized_events[index]
            if action in {"CONNECTED", "DISCONNECTED"}:
                players.pop(player_name, None)
                index += 1
                continue
            current_team = players.get(player_name)
            if (old_team == "None" and current_team is not None) or (
                old_team != "None" and current_team != old_team
            ):
                conflicts += 1
            if new_team == "None":
                players.pop(player_name, None)
            else:
                players[player_name] = new_team
            index += 1

        allies = sum(team == "Allies" for team in players.values())
        axis = sum(team == "Axis" for team in players.values())
        max_players = max(max_players, allies + axis)
        points.append(
            {
                "updated_at": _utc_iso(sample_time),
                "team_counts": {"allies": allies, "axis": axis},
                "team_difference": allies - axis,
            }
        )
        sample_time += timedelta(seconds=sample_seconds)

    anomaly_count = invalid_events + conflicts
    anomaly_rate = anomaly_count / max(1, len(ordered_events))
    reliable = (
        team_switch_events >= 20
        and max_players >= minimum_players
        and anomaly_rate <= 0.1
    )

    eligible_start = start + timedelta(seconds=round_start_protection_seconds)
    eligible_end = end - timedelta(seconds=round_end_protection_seconds)
    def is_eligible(point: dict[str, Any]) -> bool:
        observed_at = datetime.fromisoformat(point["updated_at"])
        return (
            eligible_start <= observed_at <= eligible_end
            and sum(point["team_counts"].values()) >= minimum_players
        )

    eligible = [
        point
        for point in points
        if is_eligible(point)
    ]
    unbalanced = [
        point
        for point in eligible
        if abs(point["team_difference"]) > target_difference
    ]

    longest_run = 0
    current_run = 0
    incident_count = 0
    incident_open = False
    for point in points:
        if not is_eligible(point):
            current_run = 0
            incident_open = False
        elif abs(point["team_difference"]) > target_difference:
            current_run += sample_seconds
            if current_run >= stable_difference_seconds and not incident_open:
                incident_count += 1
                incident_open = True
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
            incident_open = False

    measurable = reliable and bool(eligible)
    if not measurable:
        status = "not_measurable"
    elif incident_count:
        status = "unbalanced"
    elif unbalanced:
        status = "transient"
    else:
        status = "balanced"

    return {
        "status": status,
        "timeline": points,
        "quality": {
            "reliable": reliable,
            "valid_events": len(normalized_events),
            "team_switch_events": team_switch_events,
            "invalid_or_conflicting_events": anomaly_count,
            "anomaly_rate": round(anomaly_rate, 4),
            "maximum_observed_players": max_players,
        },
        "metrics": {
            "eligible_samples": len(eligible),
            "balanced_ratio": (
                round((len(eligible) - len(unbalanced)) / len(eligible), 4)
                if measurable
                else None
            ),
            "unbalanced_seconds": len(unbalanced) * sample_seconds,
            "longest_unbalanced_seconds": longest_run,
            "maximum_difference": max(
                (abs(point["team_difference"]) for point in eligible), default=None
            ),
            "incident_count": incident_count,
        },
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
    ) -> dict[str, Any] | None:
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
            events = session.execute(
                select(
                    LogLine.event_time,
                    LogLine.player1_name,
                    LogLine.type,
                    LogLine.content,
                )
                .where(
                    LogLine.server == str(self.server_number),
                    LogLine.event_time >= game.start,
                    LogLine.event_time <= game.end,
                    LogLine.type.in_(["TEAMSWITCH", "CONNECTED", "DISCONNECTED"]),
                )
                .order_by(LogLine.event_time)
            ).all()

            analysis = reconstruct_round_timeline(
                game.start,
                game.end,
                events,
                target_difference=target_difference,
                minimum_players=minimum_players,
                round_start_protection_seconds=round_start_protection_seconds,
                round_end_protection_seconds=round_end_protection_seconds,
                stable_difference_seconds=stable_difference_seconds,
            )
            analysis["round"] = {
                "map_id": game.id,
                "round_id": _round_id(game),
                "map_name": game.map_name,
                "start": _utc_iso(game.start),
                "end": _utc_iso(game.end),
            }
            return analysis
