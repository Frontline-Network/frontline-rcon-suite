"""Apply an explicit, evidence-backed historical playtime plan (dry run by default).

Called with a JSON bundle on stdin: evidence, boundaries, plan, apply (bool).
The operator must first retain and verify a database backup and the immutable
evidence bundle. No RCON commands, configuration edits or full-round rewrites.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from rcon.models import get_engine
from rcon.playtime_reconstruction import reconstruct, utc

if not __debug__:
    raise RuntimeError("Run this guarded maintenance tool without Python -O")

FIELDS = {"time_seconds", "kills_per_minute", "deaths_per_minute"}


def canonical(value):
    return json.loads(json.dumps(value, default=str))


def validate_plan(evidence, boundaries, plan):
    """Recalculate, never trust proposed replacement values from a manifest."""
    rows = {e["before"]["id"]: e for e in evidence}
    assert len(rows) == len(evidence), "Duplicate evidence rows"
    assert len({p["id"] for p in plan["rows"]}) == len(plan["rows"])
    assert set(rows) == {p["id"] for p in plan["rows"]}
    selected = []
    for p in plan["rows"]:
        e = rows[p["id"]]
        m = e["round"]
        assert m["server_number"] in (3, 4), "Unauthorized server"
        assert p["server_number"] == m["server_number"]
        assert p["map_id"] == m["id"] == e["before"]["map_id"]
        if m["id"] in boundaries:
            e["markers"] = [
                x
                for x in boundaries[m["id"]]
                if utc(m["start"]) <= utc(x["event_time"]) <= utc(m["end"])
            ]
        result = reconstruct(e)
        assert result == {
            k: v for k, v in p.items() if k not in ("id", "map_id", "server_number")
        }, "Plan no longer matches the evidence"
        if result["status"] == "reconstructable":
            assert set(result["after"]) == FIELDS
            selected.append((e, result))
    assert selected, "No supported repairs"
    return selected


def run(bundle):
    boundaries = {x["map_id"]: x["markers"] for x in bundle["boundaries"]}
    selected = validate_plan(bundle["evidence"], boundaries, bundle["plan"])
    applying = bundle.get("apply") is True
    ids = [e["before"]["id"] for e, _ in selected]
    expected = {e["before"]["id"]: e["before"] for e, _ in selected}
    replacement = {e["before"]["id"]: r["after"] for e, r in selected}
    counts = Counter()
    for e, _ in selected:
        counts[e["round"]["server_number"]] += 1
    with Session(get_engine()) as s:
        s.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        s.execute(text("SET LOCAL statement_timeout='30s'"))
        s.execute(text("SET LOCAL lock_timeout='3s'"))
        # Prevent another invocation while allowing unrelated application work.
        assert s.scalar(text("SELECT pg_try_advisory_xact_lock(931025,34)"))
        locked = s.execute(
            text(
                "SELECT row_to_json(p) AS row FROM player_stats p WHERE id=ANY(:ids) ORDER BY id FOR UPDATE"
            ),
            {"ids": ids},
        ).mappings()
        current = {x["row"]["id"]: x["row"] for x in locked}
        assert set(current) == set(expected), "Rows disappeared"
        if all(current[k] == {**expected[k], **replacement[k]} for k in ids):
            s.rollback()
            return {"status": "already_applied", "rows": len(ids), "by_server": counts}
        assert (
            current == expected
        ), "A complete row changed since the evidence snapshot; aborting"
        checked_maps = set()
        for index, (e, _) in enumerate(selected):
            m = e["round"]
            a, b = utc(m["start"]).replace(tzinfo=None), utc(m["end"]).replace(
                tzinfo=None
            )
            args = {
                "n": str(m["server_number"]),
                "sn": m["server_number"],
                "pid": e["before"]["playersteamid_id"],
                "a": a,
                "b": b,
            }

            def q(sql, **extra):
                return canonical(
                    [
                        dict(r)
                        for r in s.execute(text(sql), {**args, **extra}).mappings()
                    ]
                )

            if m["id"] not in checked_maps:
                actual = s.scalar(
                    text(
                        "SELECT row_to_json(m) FROM map_history m WHERE id=:id FOR SHARE"
                    ),
                    {"id": m["id"]},
                )
                assert actual == m, "Round changed since collection"
                markers = q(
                    "SELECT id,event_time,type FROM log_lines WHERE server=:n AND event_time BETWEEN :a AND :b AND type IN ('MATCH START','MATCH ENDED') ORDER BY event_time,id"
                )
                assert markers == e["markers"], "Round evidence changed"
                checked_maps.add(m["id"])
            transitions = q(
                "SELECT id,event_time,type FROM log_lines WHERE server=:n AND player1_steamid=:pid AND event_time BETWEEN :lo AND :hi AND type IN ('CONNECTED','DISCONNECTED') ORDER BY event_time,id",
                lo=a - timedelta(days=1),
                hi=b + timedelta(days=1),
            )
            sessions = q(
                'SELECT id,start,"end",server_number FROM player_sessions WHERE playersteamid_id=:pid AND server_number=:sn AND (start<=:b OR start IS NULL) AND ("end">=:a OR "end" IS NULL) ORDER BY start,id'
            )
            activity = q(
                "SELECT id,event_time,type,player1_steamid,player2_steamid FROM log_lines WHERE server=:n AND event_time BETWEEN :a AND :b AND (player1_steamid=:pid OR player2_steamid=:pid) ORDER BY event_time,id"
            )
            assert transitions == e["transitions"], "Connection evidence changed"
            assert sessions == e["sessions"], "Session evidence changed"
            assert activity == e["activity"], "Activity evidence changed"
            if (index + 1) % 500 == 0:
                print(
                    json.dumps({"stage": "revalidated", "rows": index + 1}),
                    file=sys.stderr,
                    flush=True,
                )
        # Exercise the same statement and checks in rehearsal, then ROLLBACK.
        # The complete original row and round were checked before any UPDATE.
        for e, r in selected:
            assert (
                s.execute(
                    text(
                        "UPDATE player_stats SET time_seconds=:time_seconds,kills_per_minute=:kills_per_minute,deaths_per_minute=:deaths_per_minute WHERE id=:id AND time_seconds<0"
                    ),
                    {"id": e["before"]["id"], **r["after"]},
                ).rowcount
                == 1
            )
        after = {
            x["row"]["id"]: x["row"]
            for x in s.execute(
                text(
                    "SELECT row_to_json(p) AS row FROM player_stats p WHERE id=ANY(:ids) ORDER BY id"
                ),
                {"ids": ids},
            ).mappings()
        }
        assert after == {
            k: {**expected[k], **replacement[k]} for k in ids
        }, "Unexpected data changes"
        if applying:
            s.commit()
        else:
            s.rollback()
    with Session(get_engine()) as s:
        s.execute(text("SET TRANSACTION READ ONLY"))
        saved = {
            x["row"]["id"]: x["row"]
            for x in s.execute(
                text(
                    "SELECT row_to_json(p) AS row FROM player_stats p WHERE id=ANY(:ids) ORDER BY id"
                ),
                {"ids": ids},
            ).mappings()
        }
        assert saved == (
            after if applying else expected
        ), "Post-transaction verification failed"
        remaining = [
            dict(r)
            for r in s.execute(
                text(
                    "SELECT m.server_number,count(*) AS negative_rows FROM player_stats p JOIN map_history m ON m.id=p.map_id WHERE p.time_seconds<0 AND m.server_number IN (3,4) GROUP BY m.server_number ORDER BY m.server_number"
                )
            ).mappings()
        ]
    return {
        "status": "applied" if applying else "rehearsal_rolled_back",
        "rows": len(ids),
        "by_server": counts,
        "remaining": remaining,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "changed_fields": sorted(FIELDS),
        "other_fields_unchanged": True,
    }


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin)), default=str))
