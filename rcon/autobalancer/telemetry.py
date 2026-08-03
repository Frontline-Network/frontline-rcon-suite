from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from rcon.models import AutobalanceSnapshot, enter_session

from .models import BalanceSnapshot


SNAPSHOT_RETENTION_DAYS = 180


def _database_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def persist_snapshot(server_number: int, snapshot: BalanceSnapshot) -> None:
    confidences = [
        player.rating.confidence
        for player in snapshot.players
        if player.player_id
    ]
    players = [
        {
            "player_id": player.player_id,
            "team": player.team,
            "role": player.role,
            "unit_id": player.unit_id,
            "unit_name": player.unit_name,
            "unit_type": player.unit_type,
            "unit_size": player.unit_size,
            "is_leader": player.is_leader,
            "connected_seconds": player.connected_seconds,
            "squad_seconds": player.squad_seconds,
            "rating": round(player.rating.value, 2),
            "rating_confidence": round(player.rating.confidence, 3),
        }
        for player in snapshot.players
        if player.player_id
    ]
    with enter_session() as session:
        session.add(
            AutobalanceSnapshot(
                server_number=server_number,
                round_id=snapshot.round_id,
                captured_at=_database_time(snapshot.captured_at),
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
                players=players,
            )
        )


def prune_snapshots(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    cutoff = _database_time(now - timedelta(days=SNAPSHOT_RETENTION_DAYS))
    with enter_session() as session:
        session.execute(
            delete(AutobalanceSnapshot).where(
                AutobalanceSnapshot.captured_at < cutoff
            )
        )
