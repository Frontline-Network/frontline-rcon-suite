#!/usr/bin/env python3
"""Measure SQL count, latency and payload size for live profile loaders.

The command is read-only and prints aggregate numbers only; player identifiers
and profile contents never leave the process.
"""

import argparse
import json
import time
from collections.abc import Callable

from sqlalchemy import event

from rcon.models import PlayerID, enter_session, get_engine
from rcon.player_history import get_live_profiles, get_profiles


def _recent_player_ids(limit: int) -> list[str]:
    with enter_session() as session:
        return [
            player_id
            for (player_id,) in (
                session.query(PlayerID.player_id)
                .order_by(PlayerID.created.desc())
                .limit(limit)
                .all()
            )
        ]


def _measure(name: str, loader: Callable, player_ids: list[str]) -> dict:
    query_count = 0

    def count_query(*_args, **_kwargs):
        nonlocal query_count
        query_count += 1

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", count_query)
    try:
        started_at = time.perf_counter()
        profiles = loader(player_ids)
        duration_ms = (time.perf_counter() - started_at) * 1000
    finally:
        event.remove(engine, "before_cursor_execute", count_query)

    payload_bytes = len(
        json.dumps(profiles, default=str, separators=(",", ":")).encode("utf-8")
    )
    field_payload_bytes = {
        field: len(
            json.dumps(
                [profile.get(field) for profile in profiles],
                default=str,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        for field in sorted({field for profile in profiles for field in profile})
    }
    return {
        "name": name,
        "players": len(player_ids),
        "profiles": len(profiles),
        "queries": query_count,
        "duration_ms": round(duration_ms, 1),
        "payload_bytes": payload_bytes,
        "field_payload_bytes": field_payload_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    limit = min(max(args.limit, 1), 100)
    player_ids = _recent_player_ids(limit)
    results = [
        _measure("full", lambda ids: get_profiles(ids, nb_sessions=1), player_ids),
        _measure("live", get_live_profiles, player_ids),
    ]
    print(json.dumps({"results": results}, separators=(",", ":")))


if __name__ == "__main__":
    main()
