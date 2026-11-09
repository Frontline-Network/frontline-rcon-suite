"""Guarded, one-off second pass for the approved 643 RCON3/4 playtimes.

Requires the original evidence, approved assessment and the complete pre-repair
scope. Defaults to a transaction rehearsal followed by ROLLBACK. The operator
must retain a fresh, verified backup before invoking this maintenance script.
No service restart, RCON action, map-boundary rewrite or combat-value change.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from rcon.models import get_engine
from rcon.playtime_followup_reconstruction import assess, dt

if not __debug__:
    raise RuntimeError("Run maintenance without Python -O")

FIELDS = {"time_seconds", "kills_per_minute", "deaths_per_minute"}
ACCEPTED = {"exact_positive", "proven_zero"}


def replacement(before, result):
    seconds = result["seconds"]
    assert result["reason"] in ACCEPTED
    assert isinstance(seconds, int) and not isinstance(seconds, bool) and seconds >= 0
    assert (seconds == 0) == (result["reason"] == "proven_zero")
    if seconds == 0:
        assert all(
            before[k] == 0 for k in ("kills", "deaths", "teamkills", "deaths_by_tk")
        )
    return {
        "time_seconds": seconds,
        "kills_per_minute": round(before["kills"] / max(seconds / 60, 1), 2),
        "deaths_per_minute": round(before["deaths"] / max(seconds / 60, 1), 2),
    }


def validate_manifest(bundle):
    records = bundle["records"]
    candidates = [r for r in records if r["section"] == "candidate"]
    players = {
        (r["server_number"], r["playersteamid_id"]): r
        for r in records
        if r["section"] == "player"
    }
    maps = {r["map_id"]: r["markers"] for r in records if r["section"] == "map"}
    details = {r["id"]: r for r in records if r["section"] == "detail"}
    approved_rows = bundle["assessment"]["rows"]
    approved = {r["id"]: r for r in approved_rows}
    expected = {r["id"]: r for r in bundle["before_scope"]}
    ids = {r["before"]["id"] for r in candidates}
    assert len(candidates) == len(ids) == len(approved_rows) == len(approved) == 1141
    assert ids == set(approved)
    assert len(expected) == len(bundle["before_scope"]) == 4731
    selected = []
    for e in candidates:
        p, m = e["before"], e["round"]
        assert m["server_number"] in (3, 4), "Unauthorized server"
        assert p["map_id"] == m["id"] and p["time_seconds"] < 0
        assert expected[p["id"]] == p, "Baseline disagrees with evidence"
        player = players[(m["server_number"], p["playersteamid_id"])]
        assert all(s["server_number"] == m["server_number"] for s in player["sessions"])
        result = assess(e, player, maps[m["id"]], details[p["id"]])
        assert (
            result == approved[p["id"]]
        ), "Approved assessment disagrees with recalculation"
        if result["reason"] in ACCEPTED:
            selected.append((e, result, replacement(p, result)))
    assert len(selected) == 643
    assert Counter(
        (e["round"]["server_number"], r["reason"]) for e, r, _ in selected
    ) == {
        (3, "exact_positive"): 183,
        (3, "proven_zero"): 292,
        (4, "exact_positive"): 24,
        (4, "proven_zero"): 144,
    }, "Selection differs from the approved 643 entries"
    return selected, expected


def canonical(rows):
    return json.loads(json.dumps([dict(r) for r in rows], default=str))


def read_scope(s, ids):
    return {
        r[0]["id"]: r[0]
        for r in s.execute(
            text(
                "SELECT row_to_json(p) FROM player_stats p WHERE id=ANY(:ids) ORDER BY id"
            ),
            {"ids": ids},
        )
    }


def run(bundle, verify_only=False):
    selected, expected = validate_manifest(bundle)
    ids = [e["before"]["id"] for e, _, _ in selected]
    after = {**expected}
    for e, _, values in selected:
        after[e["before"]["id"]] = {**e["before"], **values}
    applying = bundle.get("apply") is True
    status = (
        "verified"
        if verify_only
        else "applied" if applying else "rehearsal_rolled_back"
    )
    if not verify_only:
        with Session(get_engine()) as s:
            s.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            s.execute(text("SET LOCAL statement_timeout='30s'"))
            s.execute(text("SET LOCAL lock_timeout='3s'"))
            assert s.scalar(
                text("SELECT pg_try_advisory_xact_lock(931025,34)")
            ), "Another repair is active"
            list(
                s.execute(
                    text(
                        "SELECT id FROM player_stats WHERE id=ANY(:ids) ORDER BY id FOR UPDATE"
                    ),
                    {"ids": ids},
                )
            )
            current = read_scope(s, list(expected))
            if current == after:
                s.rollback()
                status = "already_applied"
            else:
                assert (
                    current == expected
                ), "Historical rows changed; aborting before any UPDATE"
                checked_maps = {}
                checked_players = {}
                for index, (e, approved, values) in enumerate(selected):
                    p, m = e["before"], e["round"]
                    a, b = (dt(m[k]).replace(tzinfo=None) for k in ("start", "end"))
                    args = {
                        "n": str(m["server_number"]),
                        "sn": m["server_number"],
                        "pid": p["playersteamid_id"],
                        "a": a,
                        "b": b,
                    }

                    def q(sql, **extra):
                        return canonical(
                            s.execute(text(sql), {**args, **extra}).mappings()
                        )

                    if m["id"] not in checked_maps:
                        actual_map = s.scalar(
                            text(
                                "SELECT row_to_json(m) FROM map_history m WHERE id=:id FOR SHARE"
                            ),
                            {"id": m["id"]},
                        )
                        assert actual_map == m, "Round changed"
                        checked_maps[m["id"]] = q(
                            "SELECT id,event_time,type,content FROM log_lines WHERE server=:n AND event_time BETWEEN :lo AND :hi AND type IN ('MATCH START','MATCH ENDED') ORDER BY event_time,id",
                            lo=a - timedelta(minutes=5),
                            hi=b + timedelta(minutes=5),
                        )
                    player_key = (m["server_number"], p["playersteamid_id"])
                    if player_key not in checked_players:
                        checked_players[player_key] = {
                            "transitions": q(
                                "SELECT id,event_time,type FROM log_lines WHERE server=:n AND player1_steamid=:pid AND type IN ('CONNECTED','DISCONNECTED') ORDER BY event_time,id"
                            ),
                            "sessions": q(
                                'SELECT id,start,"end",server_number FROM player_sessions WHERE server_number=:sn AND playersteamid_id=:pid ORDER BY start,id'
                            ),
                        }
                    detail = {
                        "activity": q(
                            "SELECT id,event_time,type,player1_steamid,player2_steamid FROM log_lines WHERE server=:n AND (player1_steamid=:pid OR player2_steamid=:pid) AND event_time BETWEEN :a AND :hi ORDER BY event_time,id",
                            hi=b + timedelta(minutes=10),
                        )
                    }
                    live_result = assess(
                        e, checked_players[player_key], checked_maps[m["id"]], detail
                    )
                    assert (
                        live_result == approved
                    ), "Fresh historical evidence no longer supports the approved duration"
                    actual_a, actual_b = (
                        dt(approved[k]).replace(tzinfo=None)
                        for k in ("actual_start", "actual_end")
                    )
                    independent = s.scalar(
                        text(
                            """SELECT coalesce(sum(extract(epoch FROM (least(z."end",:b)-greatest(z.start,:a)))),0)::int
                        FROM (SELECT DISTINCT start,"end" FROM player_sessions WHERE server_number=:n AND playersteamid_id=:pid
                        AND start<=:b AND "end">=:a AND "end">=start) z"""
                        ),
                        {
                            "n": m["server_number"],
                            "pid": p["playersteamid_id"],
                            "a": actual_a,
                            "b": actual_b,
                        },
                    )
                    assert (
                        independent == values["time_seconds"]
                    ), "Independent session calculation disagrees"
                    if (index + 1) % 200 == 0:
                        print(
                            json.dumps(
                                {
                                    "stage": "fresh_evidence_revalidated",
                                    "rows": index + 1,
                                }
                            ),
                            file=sys.stderr,
                            flush=True,
                        )
                # Both rehearsal and apply use the identical bounded statement.
                for e, _, values in selected:
                    assert (
                        s.execute(
                            text(
                                "UPDATE player_stats SET time_seconds=:time_seconds,kills_per_minute=:kills_per_minute,deaths_per_minute=:deaths_per_minute WHERE id=:id AND time_seconds<0"
                            ),
                            {"id": e["before"]["id"], **values},
                        ).rowcount
                        == 1
                    )
                assert (
                    read_scope(s, list(expected)) == after
                ), "Unexpected fields or excluded rows changed"
                if applying:
                    s.commit()
                else:
                    s.rollback()
    with Session(get_engine()) as s:
        s.execute(text("SET TRANSACTION READ ONLY"))
        s.execute(text("SET LOCAL statement_timeout='30s'"))
        saved = read_scope(s, list(expected))
        assert saved == (
            after
            if verify_only or applying or status == "already_applied"
            else expected
        ), "Post-transaction verification failed"
        remaining = canonical(
            s.execute(
                text(
                    "SELECT m.server_number,count(*) AS negative_rows FROM player_stats p JOIN map_history m ON m.id=p.map_id WHERE p.time_seconds<0 AND m.server_number IN (3,4) GROUP BY m.server_number ORDER BY m.server_number"
                )
            ).mappings()
        )
    return {
        "status": status,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "rows": 643,
        "by_server": {"3": 475, "4": 168},
        "positive": 207,
        "proven_zero": 436,
        "all_original_rows_compared": len(expected),
        "previously_repaired_unchanged": 3590,
        "excluded_unchanged": 498,
        "changed_fields": sorted(FIELDS),
        "other_fields_unchanged": True,
        "remaining": remaining,
    }


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin))))
