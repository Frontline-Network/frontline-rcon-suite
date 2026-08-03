from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from rcon.models import (
    AutobalancePlayerRoleStats,
    AutobalanceSnapshot,
    enter_session,
)

from .models import BalanceSnapshot, PlayerSnapshot
from .rating import RATING_MODEL_VERSION, role_family

SNAPSHOT_RETENTION_DAYS = 180
MAX_EXACT_INTERVAL_SECONDS = 90
COUNTER_FIELDS = (
    "kills",
    "deaths",
    "teamkills",
    "combat",
    "offense",
    "defense",
    "support",
)


def _database_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _player_payload(player: PlayerSnapshot) -> dict[str, Any]:
    return {
        "player_id": player.player_id,
        "name": player.name,
        "team": player.team,
        "role": player.role,
        "level": player.level,
        "unit_id": player.unit_id,
        "unit_name": player.unit_name,
        "unit_type": player.unit_type,
        "unit_size": player.unit_size,
        "is_leader": player.is_leader,
        "connected_seconds": player.connected_seconds,
        "squad_seconds": player.squad_seconds,
        "map_playtime_seconds": player.map_playtime_seconds,
        "kills": player.kills,
        "deaths": player.deaths,
        "teamkills": player.teamkills,
        "combat": player.combat,
        "offense": player.offense,
        "defense": player.defense,
        "support": player.support,
        "rating": player.rating.asdict(),
        "rating_model_version": player.rating.version,
        "role_family": player.rating.role_family or role_family(player),
    }


def snapshot_role_deltas(
    previous_players: list[dict[str, Any]],
    current_players: list[dict[str, Any]],
    elapsed_seconds: int,
) -> list[dict[str, Any]]:
    """Return exact, ambiguous or invalid per-player intervals for rollup."""
    previous = {
        str(player.get("player_id")): player
        for player in previous_players
        if player.get("player_id")
    }
    result: list[dict[str, Any]] = []
    for current in current_players:
        player_id = str(current.get("player_id") or "")
        before = previous.get(player_id)
        if not player_id or before is None:
            continue
        current_family = str(current.get("role_family") or role_family(current))
        previous_family = str(before.get("role_family") or role_family(before))
        row = {
            "player_id": player_id,
            "role_family": current_family,
            "time_seconds": 0,
            "valid_intervals": 0,
            "ambiguous_intervals": 0,
            "invalid_intervals": 0,
            **{field: 0 for field in COUNTER_FIELDS},
        }
        if (
            elapsed_seconds <= 0
            or elapsed_seconds > MAX_EXACT_INTERVAL_SECONDS
            or current_family != previous_family
        ):
            row["ambiguous_intervals"] = 1
            result.append(row)
            continue
        deltas = {
            field: int(current.get(field) or 0) - int(before.get(field) or 0)
            for field in COUNTER_FIELDS
        }
        if any(value < 0 for value in deltas.values()):
            row["invalid_intervals"] = 1
            result.append(row)
            continue
        row.update(deltas)
        row["time_seconds"] = elapsed_seconds
        row["valid_intervals"] = 1
        result.append(row)
    return result


def _upsert_role_delta(
    session,
    *,
    server_number: int,
    round_id: str,
    map_name: str,
    captured_at: datetime,
    delta: dict[str, Any],
) -> None:
    values = {
        "server_number": server_number,
        "round_id": round_id,
        "map_name": map_name,
        "player_id": delta["player_id"],
        "role_family": delta["role_family"],
        "first_seen": captured_at,
        "last_seen": captured_at,
        "updated_at": datetime.utcnow(),
        **{field: int(delta.get(field) or 0) for field in COUNTER_FIELDS},
        "time_seconds": int(delta.get("time_seconds") or 0),
        "valid_intervals": int(delta.get("valid_intervals") or 0),
        "ambiguous_intervals": int(delta.get("ambiguous_intervals") or 0),
        "invalid_intervals": int(delta.get("invalid_intervals") or 0),
    }
    statement = insert(AutobalancePlayerRoleStats).values(**values)
    excluded = statement.excluded
    additive = (
        "time_seconds",
        *COUNTER_FIELDS,
        "valid_intervals",
        "ambiguous_intervals",
        "invalid_intervals",
    )
    statement = statement.on_conflict_do_update(
        constraint="unique_autobalance_player_role_stats",
        set_={
            "map_name": excluded.map_name,
            "last_seen": excluded.last_seen,
            "updated_at": excluded.updated_at,
            **{
                field: getattr(AutobalancePlayerRoleStats, field)
                + getattr(excluded, field)
                for field in additive
            },
        },
    )
    session.execute(statement)


def persist_snapshot(server_number: int, snapshot: BalanceSnapshot) -> None:
    confidences = [
        player.rating.confidence for player in snapshot.players if player.player_id
    ]
    players = [
        _player_payload(player) for player in snapshot.players if player.player_id
    ]
    captured_at = _database_time(snapshot.captured_at)
    with enter_session() as session:
        previous = session.scalar(
            select(AutobalanceSnapshot)
            .where(
                AutobalanceSnapshot.server_number == server_number,
                AutobalanceSnapshot.round_id == snapshot.round_id,
                AutobalanceSnapshot.captured_at < captured_at,
            )
            .order_by(AutobalanceSnapshot.captured_at.desc())
            .limit(1)
        )
        if previous is not None:
            elapsed = int((captured_at - previous.captured_at).total_seconds())
            for delta in snapshot_role_deltas(previous.players, players, elapsed):
                _upsert_role_delta(
                    session,
                    server_number=server_number,
                    round_id=snapshot.round_id,
                    map_name=snapshot.map_name,
                    captured_at=captured_at,
                    delta=delta,
                )
        session.add(
            AutobalanceSnapshot(
                server_number=server_number,
                round_id=snapshot.round_id,
                captured_at=captured_at,
                map_name=snapshot.map_name,
                map_elapsed_seconds=snapshot.map_elapsed_seconds,
                time_remaining_seconds=snapshot.time_remaining_seconds,
                allies_count=snapshot.allies_count,
                axis_count=snapshot.axis_count,
                counts_match=snapshot.counts_match,
                fail_count=snapshot.fail_count,
                stable_map=snapshot.stable_map,
                rating_confidence=(
                    sum(confidences) / len(confidences) if confidences else None
                ),
                rating_model_version=RATING_MODEL_VERSION,
                players=players,
            )
        )


def prune_snapshots(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    cutoff = _database_time(now - timedelta(days=SNAPSHOT_RETENTION_DAYS))
    with enter_session() as session:
        session.execute(
            delete(AutobalanceSnapshot).where(AutobalanceSnapshot.captured_at < cutoff)
        )
        session.execute(
            delete(AutobalancePlayerRoleStats).where(
                AutobalancePlayerRoleStats.last_seen < cutoff
            )
        )
