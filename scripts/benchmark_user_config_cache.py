#!/usr/bin/env python3
"""Measure aggregate SQL work for the hot Automod configuration path.

The benchmark is read-only and deliberately reports no configuration values.
Run it inside a backend or supervisor container with the normal database and
Redis environment available.
"""

import argparse
import json
import time

from sqlalchemy import event

from rcon.automods.automod import enabled_moderators
from rcon.models import get_engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")

    query_count = 0

    def count_query(*_args):
        nonlocal query_count
        query_count += 1

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", count_query)
    started = time.perf_counter()
    try:
        for _ in range(args.iterations):
            enabled_moderators()
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        event.remove(engine, "before_cursor_execute", count_query)

    print(
        json.dumps(
            {
                "iterations": args.iterations,
                "sql_queries": query_count,
                "elapsed_ms": round(elapsed_ms, 1),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
