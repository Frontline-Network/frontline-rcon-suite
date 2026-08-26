"""Read-only SQL query benchmark for incident list endpoints.

Only aggregate counts and timings are printed. Incident contents never leave the
process, which makes the script safe to use during production validation.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import event

from rcon.admin_incidents import list_incident_changes, list_incidents
from rcon.models import get_engine


def measure(function: Callable[[], Any]) -> dict[str, int | float]:
    engine = get_engine()
    query_count = 0

    def count_query(*_args: Any) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", count_query)
    started = time.perf_counter()
    try:
        result = function()
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        event.remove(engine, "before_cursor_execute", count_query)

    items = result[0] if isinstance(result, tuple) else result
    return {
        "items": len(items),
        "queries": query_count,
        "elapsed_ms": elapsed_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    limit = min(max(args.limit, 1), 250)

    print(
        json.dumps(
            {
                "incident_list": measure(lambda: list_incidents(limit=limit)),
                "incident_changes": measure(
                    lambda: list_incident_changes(0, limit=limit)
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
