"""Inspect and explicitly resolve unidentified local session events."""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def inspect_unidentified(path: str, server: int, limit: int = 100, *, include_resolved: bool = False) -> list[dict]:
    if server < 1 or not 1 <= limit <= 1000:
        raise ValueError("Invalid server or limit")
    uri = Path(path).resolve(strict=True).as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        rows = db.execute(
            "SELECT rowid, kind, event_us, player_name, raw, resolved_at, resolved_by, resolution_reason "
            "FROM unidentified_session_events WHERE server = ? AND (? OR resolved_at IS NULL) "
            "ORDER BY event_us, kind, player_name LIMIT ?",
            (server, include_resolved, limit),
        ).fetchall()
    return [{"id": event_id, "kind": kind, "event_us": str(event_us),
             "event_time": datetime.fromtimestamp(event_us / 1_000_000, timezone.utc).isoformat(),
             "player_name": name, "raw": raw,
             "resolved_at": datetime.fromtimestamp(resolved_at, timezone.utc).isoformat() if resolved_at is not None else None,
             "resolved_by": resolved_by, "resolution_reason": reason}
            for event_id, kind, event_us, name, raw, resolved_at, resolved_by, reason in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", help="Path to the existing server journal")
    parser.add_argument("--server", required=True, type=int)
    parser.add_argument("--limit", default=100, type=int)
    parser.add_argument("--include-resolved", action="store_true", help="Include recorded review decisions")
    parser.add_argument("--discard-id", type=int, help="Mark one verified event as discarded")
    parser.add_argument("--actor", help="Operator name; required when discarding")
    parser.add_argument("--reason", help="Review reason; required when discarding")
    args = parser.parse_args()
    if args.discard_id is not None:
        if not args.actor or not args.reason:
            parser.error("--actor and --reason are required with --discard-id")
        from rcon.session_event_journal import SessionEventJournal
        path = Path(args.journal).resolve(strict=True)
        changed = SessionEventJournal(path).discard_unidentified(args.server, args.discard_id, args.actor, args.reason)
        if not changed:
            parser.error("Event not found, belongs to another server or is already resolved")
        print(json.dumps({"discarded": args.discard_id}))
        return
    print(json.dumps(inspect_unidentified(args.journal, args.server, args.limit,
                                          include_resolved=args.include_resolved), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
