from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select

from rcon.models import Maps, PlayerID, PlayerStats, enter_session

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
