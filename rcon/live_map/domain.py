"""Pure telemetry rules. No network calls, player messages or moderation actions."""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict

from rcon.live_map.projections import projection_ready

RULE_VERSION = "2"
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
    if point is None or not projection_ready(calibration):
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


def segment_break(previous, current, previous_time, current_time, units_per_meter=None, display_only=False):
    if not previous or not current.get("position_valid") or not previous.get("position_valid"):
        return True
    elapsed = current_time - previous_time
    if elapsed <= 0 or elapsed > 12 or current.get("team") != previous.get("team"):
        return True
    if current.get("session_id") != previous.get("session_id") or current.get("deaths") != previous.get("deaths"):
        return True
    if units_per_meter:
        return distance(previous["position"], current["position"]) / units_per_meter > max(150, elapsed * 100)
    if display_only:
        a, b = previous.get("map_position"), current.get("map_position")
        # Only a visual trace: cut jumps above 10% of an image edge (or 5%/s).
        # No physical distance or movement-speed claim is derived from this.
        return not a or not b or distance(a, b) > max(.1, elapsed * .05)
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


def _weapon_category(weapon):
    # Use the shared game profiles. Explosives, mines, commander abilities and
    # other multi-kill sources remain context, but never count as infantry
    # kill-rate or burst evidence.
    from rcon.weapons import ALL_WEAPONS, WeaponType

    kind = ALL_WEAPONS.get(weapon)
    if kind is None:
        try:
            from rcon.game.hllv.weapons import HLLV_WEAPONS

            kind = HLLV_WEAPONS.get(weapon)
        except (ImportError, RuntimeError):
            kind = None
    if kind == WeaponType.Armor:
        return "armor"
    if kind in {WeaponType.Artillery, WeaponType.SPA}:
        return "artillery"
    if kind == WeaponType.MachineGun:
        return "mg"
    if kind in {WeaponType.Infantry, WeaponType.Sniper}:
        return "infantry"
    return None


def _burst(events, count, unique_victims, seconds):
    start = 0
    for end, event in enumerate(events):
        while event["time"] - events[start]["time"] > seconds:
            start += 1
        window = events[start : end + 1]
        if len(window) >= count and len({item["victim"] for item in window}) >= unique_victims:
            return window
    return []


def _movement_anomalies(frames, round_id, profile):
    """Return repeated, metrically verified jumps without labelling their cause."""
    previous, consecutive, qualified, result = (
        {},
        defaultdict(int),
        set(),
        defaultdict(list),
    )
    limit = float(profile["movement_mps"])
    required = int(profile["movement_consecutive"])
    for frame in sorted(
        (item for item in frames if item.get("round_id") == round_id),
        key=lambda item: item["captured_at"],
    ):
        captured = frame["captured_at"]
        for player in frame.get("players", []):
            player_id = player.get("player_id")
            prior = previous.get(player_id)
            previous[player_id] = (captured, player)
            if not prior or not player.get("position_m") or not prior[1].get("position_m"):
                consecutive[player_id] = 0
                continue
            prior_time, prior_player = prior
            elapsed = captured - prior_time
            comparable = (
                0 < elapsed <= 12
                and player.get("session_id") == prior_player.get("session_id")
                and player.get("team") == prior_player.get("team")
                and player.get("deaths") == prior_player.get("deaths")
            )
            if not comparable:
                consecutive[player_id] = 0
                continue
            speed = distance(prior_player["position_m"], player["position_m"]) / elapsed
            if speed <= limit:
                consecutive[player_id] = 0
                continue
            consecutive[player_id] += 1
            result[player_id].append(
                {
                    "time": captured,
                    "speed_mps": round(speed, 1),
                    "from": prior_player.get("map_position"),
                    "to": player.get("map_position"),
                }
            )
            if consecutive[player_id] >= required:
                qualified.add(player_id)
    return {player_id: result[player_id] for player_id in qualified}


def evaluate_gameplay_patterns(events, frames, now, round_id, first_seen, profile, metric_ready):
    """Build explainable review candidates; never returns an enforcement action."""
    unique = {
        event["id"]: event
        for event in events
        if event.get("round_id") == round_id
        and not event.get("teamkill")
        and event.get("attacker")
        and event.get("victim")
        and event.get("time", now + 1) <= now
    }
    by_attacker = defaultdict(list)
    for event in unique.values():
        by_attacker[event["attacker"]].append(event)
    for values in by_attacker.values():
        values.sort(key=lambda item: item["time"])

    players = {}
    for frame in frames:
        for player in frame.get("players", []):
            players[player.get("player_id")] = player
    movement = _movement_anomalies(frames, round_id, profile) if metric_ready else {}
    result = []
    for player_id in set(by_attacker) | set(movement):
        kills = by_attacker.get(player_id, [])
        signals, rates = [], {}
        observed_start = float(first_seen.get(player_id, now))
        observed_seconds = max(0.0, now - observed_start)
        scored_kills = [event for event in kills if event["time"] >= observed_start]
        categories = defaultdict(list)
        for event in scored_kills:
            category = _weapon_category(event.get("weapon"))
            if category:
                categories[category].append(event)
        relevant_kills = [event for values in categories.values() for event in values]
        played = max(60.0, observed_seconds)
        for category, values in categories.items():
            rate = len(values) / played * 60
            rates[category] = round(rate, 2)
            threshold = float(profile[f"killrate_{category}"])
            if (
                observed_seconds >= 60
                and len(values) >= int(profile["min_kills"])
                and rate >= threshold
            ):
                signals.append(
                    {
                        "kind": "kill_rate",
                        "category": category,
                        "kills": len(values),
                        "kpm": round(rate, 2),
                        "threshold": threshold,
                    }
                )
        infantry = categories.get("infantry", [])
        burst = _burst(
            infantry,
            int(profile["burst_kills"]),
            int(profile["burst_unique_victims"]),
            int(profile["burst_seconds"]),
        )
        if burst:
            signals.append(
                {
                    "kind": "kill_burst",
                    "kills": len(burst),
                    "unique_victims": len({event["victim"] for event in burst}),
                    "seconds": round(burst[-1]["time"] - burst[0]["time"], 1),
                }
            )
        recent_pairs = defaultdict(list)
        for event in kills:
            if now - WINDOW_SECONDS <= event["time"]:
                recent_pairs[event["victim"]].append(event)
        repeated = max(recent_pairs.values(), key=len, default=[])
        if len(repeated) >= 3:
            signals.append(
                {
                    "kind": "repeated_target",
                    "victim": repeated[-1]["victim"],
                    "victim_name": repeated[-1].get("victim_name"),
                    "kills": len(repeated),
                    "seconds": round(repeated[-1]["time"] - repeated[0]["time"], 1),
                }
            )
        jumps = movement.get(player_id, [])
        if jumps:
            signals.append(
                {
                    "kind": "movement_anomaly",
                    "count": len(jumps),
                    "maximum_mps": max(item["speed_mps"] for item in jumps),
                    "threshold_mps": float(profile["movement_mps"]),
                    "diagnostic_only": True,
                }
            )
        if not signals:
            continue
        combat = any(item["kind"] in {"kill_rate", "kill_burst"} for item in signals)
        severity = "high" if combat and len(signals) >= 3 else "review" if combat and len(signals) >= 2 else "observation"
        player = players.get(player_id, {})
        times = [event["time"] for event in kills]
        times += [item["time"] for item in jumps]
        first_at, last_at = min(times or [now]), max(times or [now])
        detection_id = hashlib.sha256(
            f"{RULE_VERSION}:{round_id}:{player_id}:gameplay_pattern".encode()
        ).hexdigest()
        result.append(
            {
                "id": detection_id,
                "round_id": round_id,
                "player_id": player_id,
                "player_name": player.get("name") or (kills[-1].get("attacker_name") if kills else None),
                "kind": "gameplay_pattern",
                "severity": severity,
                "first_at": first_at,
                "last_at": last_at,
                "rule_version": RULE_VERSION,
                "signals": signals,
                "metrics": {
                    "kills": len(relevant_kills),
                    "all_logged_kills": len(kills),
                    "playtime_seconds": round(played),
                    "observed_seconds": round(observed_seconds),
                    "kills_per_minute": rates,
                    "unique_victims": len({event["victim"] for event in kills}),
                },
                "events": relevant_kills[-50:],
                "movement_events": jumps[-20:],
                "data_quality": {
                    "metric_positions": bool(metric_ready),
                    "movement_assessed": bool(metric_ready),
                    "position_note": "Positionssprünge sind ein technischer Prüfkontext und kein eigenständiger Cheatnachweis.",
                },
                "context": [
                    "Waffen, Rollen, Fahrzeuge, Spawnkämpfe und gemeinsame Frontabschnitte prüfen.",
                    "Keine Schussrichtung, Sichtlinie, Trefferquote oder Client-Anti-Cheat-Daten vorhanden.",
                    "Der Hinweis ist keine Cheat-Wahrscheinlichkeit und löst keine automatische Maßnahme aus.",
                ],
            }
        )
    return sorted(
        result,
        key=lambda item: (
            {"high": 2, "review": 1, "observation": 0}[item["severity"]],
            item["last_at"],
        ),
        reverse=True,
    )


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
