"""Read-only follow-up classification. Never supplies executable UPDATEs."""

from collections import Counter
from datetime import datetime, timezone


def dt(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def assess(candidate, player, markers, detail):
    p = candidate["before"]
    m = candidate["round"]
    a = dt(m["start"])
    b = dt(m["end"])

    def result(reason, **extra):
        return {
            "id": p["id"],
            "server": m["server_number"],
            "map_id": m["id"],
            "old_seconds": p["time_seconds"],
            "reason": reason,
            **extra,
        }

    if not 0 < (b - a).total_seconds() <= 14400:
        return result("damaged_or_unusually_long_round")
    inside = {
        (dt(x["event_time"]), x["type"])
        for x in markers
        if a <= dt(x["event_time"]) <= b
    }
    starts = sorted(t for t, kind in inside if kind == "MATCH START")
    ends = sorted(t for t, kind in inside if kind == "MATCH ENDED")
    if starts not in ([a], [a, b]):
        return result("unconfirmed_start")
    if len(ends) != 1:
        return result("missing_match_end", known_next_start=(starts == [a, b]))
    actual_end = ends[0]
    if not a < actual_end <= b:
        return result("invalid_round_end")
    if actual_end < b and starts != [a, b]:
        return result("unconfirmed_intermission")
    markers_proof = [
        x["id"]
        for x in markers
        if (dt(x["event_time"]), x["type"])
        in ((a, "MATCH START"), (actual_end, "MATCH ENDED"))
    ]
    intermission_seconds = int((b - actual_end).total_seconds())
    transitions = []
    seen = set()
    for t in player["transitions"]:
        key = (dt(t["event_time"]), t["type"])
        if key not in seen:
            transitions.append({**t, "moment": key[0]})
            seen.add(key)
    intervals = []
    uncertain = []
    opened = None
    last_disconnect = None
    for t in transitions:
        moment = t["moment"]
        if t["type"] == "CONNECTED":
            if opened is not None:
                uncertain.append(
                    (opened["moment"], moment, "connect_without_disconnect")
                )
            opened = t
        elif t["type"] == "DISCONNECTED":
            if opened is not None:
                if opened["moment"] > moment:
                    return result("reversed_connection")
                intervals.append((opened, t))
                opened = None
            elif a <= moment <= actual_end:
                uncertain.append(
                    (last_disconnect or a, moment, "disconnect_without_connect")
                )
            last_disconnect = moment
    if opened and opened["moment"] < actual_end:
        uncertain.append((opened["moment"], actual_end, "missing_disconnect"))
    for lo, hi, why in uncertain:
        if max(lo, a) < min(hi, actual_end):
            later = [
                x
                for x in detail["activity"]
                if dt(x["event_time"]) > actual_end
                and x["type"]
                not in ("CONNECTED", "DISCONNECTED", "MESSAGE", "ADMIN MESSAGE")
            ]
            return result(
                why,
                has_postround_presence=bool(later),
                intermission_seconds=intermission_seconds,
            )
    overlapping = [
        (x, y) for x, y in intervals if x["moment"] <= actual_end and y["moment"] >= a
    ]
    session_proofs = []
    ignored_stale = []
    incomplete_corroboration = []
    for ss in player["sessions"]:
        sa = dt(ss["start"]) if ss["start"] else None
        sb = dt(ss["end"]) if ss["end"] else None
        if sa is not None and sa > actual_end:
            continue
        if sb is not None and sb < a:
            continue
        if sa and sb is None:
            previous_disconnect = next(
                (
                    t
                    for t in transitions
                    if t["type"] == "DISCONNECTED" and sa <= t["moment"] <= a
                ),
                None,
            )
            if previous_disconnect:
                ignored_stale.append(
                    {
                        "session_id": ss["id"],
                        "disconnected_log_id": previous_disconnect["id"],
                    }
                )
                continue
            exact_pair = next(
                ((x, y) for x, y in overlapping if x["moment"] == sa), None
            )
            if exact_pair:
                incomplete_corroboration.append(ss["id"])
                continue
            return result(
                "unresolved_open_session", intermission_seconds=intermission_seconds
            )
        if sa is None or sb is None:
            return result("unresolved_session_start")
        if not any(x["moment"] == sa and y["moment"] == sb for x, y in overlapping):
            return result("closed_session_log_conflict")
        session_proofs.append(ss["id"])
    for x, y in overlapping:
        if not any(
            ss["start"]
            and dt(ss["start"]) == x["moment"]
            and (ss["end"] is None or dt(ss["end"]) == y["moment"])
            for ss in player["sessions"]
        ):
            return result("uncorroborated_connection")
    clipped = [
        (max(x["moment"], a), min(y["moment"], actual_end)) for x, y in overlapping
    ]
    activity = [x for x in detail["activity"] if a <= dt(x["event_time"]) <= actual_end]
    if any(
        not any(lo <= dt(x["event_time"]) <= hi for lo, hi in clipped) for x in activity
    ):
        return result("activity_outside_proven_connection")
    counts = Counter({"kills": 0, "deaths": 0, "teamkills": 0, "deaths_by_tk": 0})
    for event in activity:
        if event["type"] in ("KILL", "TEAM KILL"):
            tk = event["type"] == "TEAM KILL"
            if event["player1_steamid"] == p["playersteamid_id"]:
                counts["teamkills" if tk else "kills"] += 1
            if event["player2_steamid"] == p["playersteamid_id"]:
                counts["deaths_by_tk" if tk else "deaths"] += 1
    if any(p[k] != v for k, v in counts.items()):
        return result("combat_count_disagreement")
    seconds = int(sum((hi - lo).total_seconds() for lo, hi in clipped))
    if seconds < 0:
        return result("negative_reconstruction")
    if seconds == 0:
        # Positive evidence of the observed join at/after the actual round end,
        # not merely absent combat or an empty set of logs.
        join = next(
            (
                x
                for x in transitions
                if x["type"] == "CONNECTED" and actual_end <= x["moment"] <= b
            ),
            None,
        )
        if join is None:
            return result("zero_without_join_evidence")
        proof = [join["id"]]
    else:
        proof = [t["id"] for pair in overlapping for t in pair]
    return result(
        "exact_positive" if seconds > 0 else "proven_zero",
        seconds=seconds,
        actual_start=a.isoformat(),
        actual_end=actual_end.isoformat(),
        intermission_seconds=intermission_seconds,
        connection_log_ids=proof,
        round_log_ids=markers_proof,
        session_ids=session_proofs,
        stale_sessions_disproved=ignored_stale,
        missing_session_end_corroborated_by_raw_logs=incomplete_corroboration,
    )
