"""Pure telemetry rules. No network calls, player messages or moderation actions."""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict

RULE_VERSION = "1"
WINDOW_SECONDS = 900
HISTORY_SECONDS = 86400
CASE_SECONDS = 30 * 86400
UNAVAILABLE = "Vom Gameserver nicht verfügbar"


def position(value):
    if not isinstance(value, dict):
        return None
    normalized = {str(k).lower(): v for k, v in value.items()}
    try:
        if any(isinstance(normalized[k], bool) for k in ("x", "y", "z")):
            return None
        result = {k: float(normalized[k]) for k in ("x", "y", "z")}
        return result if all(math.isfinite(v) for v in result.values()) else None
    except (KeyError, ValueError, TypeError):
        return None


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def project(point, calibration):
    if point is None or not calibration or not calibration.get("verified"):
        return None
    a, b, c, d, e, f = calibration["matrix"]
    x, y = point["x"], point["y"]
    uv = {"x": a * x + b * y + c, "y": d * x + e * y + f}
    return uv if all(0 <= v <= 1 for v in uv.values()) else None


def _solve(matrix, values):
    rows = [list(row) + [val] for row, val in zip(matrix, values)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda i: abs(rows[i][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        if abs(rows[col][col]) < 1e-12:
            raise ValueError("Referenzpunkte liegen auf einer Geraden")
        scale = rows[col][col]
        rows[col] = [v / scale for v in rows[col]]
        for row in range(3):
            if row != col:
                scale = rows[row][col]
                rows[row] = [v - scale * w for v, w in zip(rows[row], rows[col])]
    return [row[-1] for row in rows]


def calibrate(points, checks, units_per_meter, source):
    """Fit three anchors; require two independent checks, with <=10 m error."""
    if len(points) != 3 or len(checks) < 2 or len(checks) > 20:
        raise ValueError("Drei Referenzpunkte und mindestens zwei unabhängige Prüfpunkte erforderlich")
    scale = float(units_per_meter)
    if not math.isfinite(scale) or not 0 < scale <= 10000 or not str(source).strip():
        raise ValueError("Maßstab und Herkunft der Referenzpunkte erforderlich")
    points = [{k: float(p[k]) for k in ("x", "y", "u", "v")} for p in points]
    checks = [{k: float(p[k]) for k in ("x", "y", "u", "v")} for p in checks]
    for p in points + checks:
        if any(not math.isfinite(float(p[k])) for k in ("x", "y", "u", "v")):
            raise ValueError("Ungültiger Referenzpunkt")
        if not all(0 <= float(p[k]) <= 1 for k in ("u", "v")):
            raise ValueError("Bildkoordinaten müssen zwischen 0 und 1 liegen")
    identities = {(p["x"], p["y"]) for p in points + checks}
    if len(identities) != len(points) + len(checks):
        raise ValueError("Prüfpunkte müssen unabhängig sein")
    matrix = [[float(p["x"]), float(p["y"]), 1] for p in points]
    a, b, c = _solve(matrix, [float(p["u"]) for p in points])
    d, e, f = _solve(matrix, [float(p["v"]) for p in points])
    determinant = a * e - b * d
    if abs(determinant) < 1e-18:
        raise ValueError("Ungültige Kartenabbildung")
    errors = []
    for p in checks:
        u, v = float(p["u"]) - c, float(p["v"]) - f
        expected = {"x": (e * u - b * v) / determinant, "y": (-d * u + a * v) / determinant}
        errors.append(distance(p, expected) / scale)
    if not all(math.isfinite(v) for v in [a, b, c, d, e, f, *errors]):
        raise ValueError("Ungültige Kartenabbildung")
    if max(errors) > 10:
        raise ValueError("Kalibrierung überschreitet zehn Meter Abweichung")
    return {"verified": True, "matrix": [a, b, c, d, e, f], "units_per_meter": scale,
            "max_error_m": max(errors), "source": str(source)[:1000], "anchors": points, "checks": checks}


def segment_break(previous, current, previous_time, current_time, units_per_meter=None):
    if not previous or not current.get("position_valid") or not previous.get("position_valid"):
        return True
    elapsed = current_time - previous_time
    if elapsed <= 0 or elapsed > 12 or current.get("team") != previous.get("team"):
        return True
    if current.get("session_id") != previous.get("session_id") or current.get("deaths") != previous.get("deaths"):
        return True
    if units_per_meter:
        return distance(previous["position"], current["position"]) / units_per_meter > max(150, elapsed * 100)
    # Without a validated scale no trajectory is advertised as continuous.
    return True


def normalize_event(log, round_id, round_start, now):
    action = str(log.get("action", "")).upper()
    if action not in {"KILL", "TEAM KILL"}:
        return None
    try:
        timestamp = float(log["timestamp_ms"]) / 1000
    except (KeyError, ValueError, TypeError):
        return None
    attacker, victim = log.get("player_id_1"), log.get("player_id_2")
    if not attacker or not victim or attacker == victim or not round_start <= timestamp <= now + 2:
        return None
    # RCON may change the relative-age prefix when returning the same raw line.
    # Absolute event time and stable player IDs, not that prefix, identify kills.
    signature = [round_id, timestamp, attacker, victim, log.get("weapon"), action]
    return {"id": hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest(),
            "round_id": round_id, "time": timestamp, "attacker": str(attacker), "victim": str(victim),
            "attacker_name": log.get("player_name_1"), "victim_name": log.get("player_name_2"),
            "weapon": log.get("weapon"), "teamkill": action == "TEAM KILL",
            "position": None, "position_m": None, "position_sample_at": None}


def observed_death_totals(frames, protected_ids, now, round_id):
    """Conservative denominator from an uninterrupted 15-minute stats window.

    Include the sample just before the cutoff, never after it: the count can
    slightly overestimate deaths but must not inflate a player's kill share.
    Resets, reconnects and missing counters make the denominator unavailable.
    """
    frames = [f for f in frames if f["round_id"] == round_id and f["captured_at"] <= now]
    cutoff = now - WINDOW_SECONDS
    baselines = [i for i, f in enumerate(frames) if f["captured_at"] <= cutoff]
    if not baselines:
        return {}
    window = frames[baselines[-1]:]
    if cutoff - window[0]["captured_at"] > 12 or now - window[-1]["captured_at"] > 12:
        return {}
    if any(b["captured_at"] - a["captured_at"] > 12 for a, b in zip(window, window[1:])):
        return {}
    samples = {p: [] for p in protected_ids}
    for frame in window:
        for player in frame["players"]:
            if player["player_id"] in samples:
                samples[player["player_id"]].append(player)
    result = {}
    for player_id, values in samples.items():
        if len(values) != len(window) or not all(p.get("deaths_valid") and p.get("session_id") for p in values):
            continue
        if any(b["session_id"] != a["session_id"] or b["deaths"] < a["deaths"] for a, b in zip(values, values[1:])):
            continue
        result[player_id] = values[-1]["deaths"] - values[0]["deaths"]
    return result


def evaluate_encounters(events, protected_ids, now, round_id, death_totals=None):
    unique = {e["id"]: e for e in events if e["round_id"] == round_id and now - WINDOW_SECONDS <= e["time"] <= now}
    deaths, pairs = defaultdict(list), defaultdict(list)
    for event in unique.values():
        deaths[event["victim"]].append(event)
        if event.get("teamkill"):
            continue
        if event["victim"] in protected_ids:
            pairs[(event["attacker"], event["victim"])].append(event)
    result = []
    for (attacker, victim), kills in pairs.items():
        kills.sort(key=lambda e: e["time"])
        points = [e["position_m"] for e in kills if e.get("position_m")]
        separated = any(distance(a, b) >= 200 for i, a in enumerate(points) for b in points[i + 1:])
        complete = victim in (death_totals or {})
        total = max(len(deaths[victim]), (death_totals or {}).get(victim, 0))
        share = len(kills) / total
        review = complete and len(kills) >= 4 and total >= 5 and share >= .6 and separated
        counterkills = sum(e["attacker"] == victim and e["victim"] == attacker and not e.get("teamkill") for e in unique.values())
        result.append({"id": hashlib.sha256(f"{round_id}:{attacker}:{victim}".encode()).hexdigest(),
                       "round_id": round_id, "attacker": attacker, "victim": victim,
                       "attacker_name": kills[-1].get("attacker_name"), "victim_name": kills[-1].get("victim_name"),
                       "count": len(kills), "total_deaths": total, "death_count_complete": complete,
                       "share": share, "counterkills": counterkills,
                       "kind": "review" if review else "repeated" if len(kills) >= 3 else "encounter",
                       "separated_areas": separated, "located_events": len(points), "events": kills,
                       "first_at": kills[0]["time"], "last_at": kills[-1]["time"], "rule_version": RULE_VERSION,
                       "context": ["Gemeinsame Kampfgebiete und Aufklärungsrollen berücksichtigen.",
                                   "Positionen sind letzte Messpunkte, keine exakten Schusspositionen.",
                                   "Kein Nachweis für Streamsniping oder Ghosting."]})
    return sorted(result, key=lambda s: (s["kind"] == "review", s["count"], s["last_at"]), reverse=True)


def redact_positions(value):
    """Strip tactical fields even inside nested/JSON-encoded legacy responses."""
    blocked = {"worldposition", "position", "positionm", "positionvalid", "mapposition", "trajectory", "positions", "garrisons", "outposts", "tacticalevidence", "pcoord"}
    if isinstance(value, dict):
        return {k: redact_positions(v) for k, v in value.items() if str(k).replace("_", "").lower() not in blocked}
    if isinstance(value, (list, tuple)):
        return [redact_positions(v) for v in value]
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            return json.dumps(redact_positions(json.loads(value)), ensure_ascii=False)
        except (ValueError, TypeError):
            pass
    return value
