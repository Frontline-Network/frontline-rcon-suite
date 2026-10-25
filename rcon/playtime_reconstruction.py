"""Conservative historical connection-time reconstruction; no database writes.

Times are UTC. This measures connected time within a round, not time alive or
spawned. Missing, contradictory or uncorroborated evidence is never imputed.
"""

from datetime import datetime, timezone


def utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def reconstruct(evidence):
    row = evidence["before"]
    match = evidence["round"]
    start, end = utc(match["start"]), utc(match["end"])

    def reject(reason):
        return {"status": "unresolved", "reason": reason}

    if row["time_seconds"] >= 0:
        return reject("not_negative")
    if not 0 < (end - start).total_seconds() <= 4 * 3600:
        return reject("invalid_or_unusually_long_round")
    if evidence.get("collection_error"):
        return reject(evidence["collection_error"])
    markers = {(utc(x["event_time"]), x["type"]) for x in evidence["markers"]}
    if markers != {(start, "MATCH START"), (end, "MATCH ENDED")}:
        return reject("round_boundaries_not_confirmed")

    # Exact duplicate transition records do not represent a second connection.
    transitions = sorted(
        {(utc(x["event_time"]), x["type"]) for x in evidence["transitions"]}
    )
    intervals = []
    opened = None
    broken = False
    for moment, kind in transitions:
        if kind == "CONNECTED":
            if opened is not None:
                broken = True
            else:
                opened = moment
        elif kind == "DISCONNECTED":
            if opened is None:
                if start <= moment <= end:
                    return reject("disconnect_without_connect")
            else:
                if moment >= start and opened <= end:
                    if broken or moment <= opened:
                        return reject("ambiguous_connection_sequence")
                    intervals.append((opened, moment))
                opened = None
                broken = False
    if opened is not None and opened <= end:
        return reject("connection_end_missing")
    if not intervals:
        return reject("no_complete_connection")

    # PlayerSession has historically not always closed with a server filter.
    # Therefore never trust it alone: require exact same-server raw transitions.
    sessions = set()
    for session in evidence["sessions"]:
        if session["server_number"] != match["server_number"]:
            continue
        if session["start"] is None or session["end"] is None:
            return reject("session_boundary_missing")
        sessions.add((utc(session["start"]), utc(session["end"])))
    if set(intervals) != sessions:
        return reject("session_log_disagreement")

    clipped = [(max(a, start), min(b, end)) for a, b in intervals]
    for previous, current in zip(clipped, clipped[1:]):
        if previous[1] > current[0]:
            return reject("overlapping_connections")
    if any(
        not any(a <= utc(event["event_time"]) <= b for a, b in clipped)
        for event in evidence["activity"]
    ):
        return reject("activity_outside_connection")
    counts = {key: 0 for key in ("kills", "deaths", "teamkills", "deaths_by_tk")}
    player_id = row["playersteamid_id"]
    for event in evidence["activity"]:
        if event["type"] in ("KILL", "TEAM KILL"):
            is_tk = event["type"] == "TEAM KILL"
            if event["player1_steamid"] == player_id:
                counts["teamkills" if is_tk else "kills"] += 1
            if event["player2_steamid"] == player_id:
                counts["deaths_by_tk" if is_tk else "deaths"] += 1
    if any(row[key] != value for key, value in counts.items()):
        return reject("combat_log_disagreement")
    seconds = int(sum((b - a).total_seconds() for a, b in clipped))
    if seconds <= 0 or seconds > (end - start).total_seconds():
        return reject("nonpositive_or_excessive_duration")
    return {
        "status": "reconstructable",
        "reason": "same_server_connection_logs_and_sessions_agree",
        "intervals": [[a.isoformat(), b.isoformat()] for a, b in clipped],
        "after": {
            "time_seconds": seconds,
            "kills_per_minute": round(row["kills"] / max(seconds / 60, 1), 2),
            "deaths_per_minute": round(row["deaths"] / max(seconds / 60, 1), 2),
        },
    }
