"""Single collector per server; HTTP readers only consume its cached output."""
import json
import logging
import threading
import time
from collections import deque

from rcon.live_map import storage
from rcon.live_map.domain import (
    evaluate_encounters,
    evaluate_gameplay_patterns,
    normalize_event,
    normalize_stored_frame,
    observed_death_totals,
    position,
    project,
    segment_break,
    vietnam_list_only,
)
from rcon.live_map.projections import display_projection, projection_ready

logger = logging.getLogger(__name__)


def key(server, suffix):
    return f"frontline:live-map:{server}:{suffix}"


def read_snapshot(red, server):
    raw = red.get(key(server, "snapshot"))
    return normalize_stored_frame(json.loads(raw)) if raw else None


def read_pending(red, server):
    raw = red.get(key(server, "pending"))
    return [normalize_stored_frame(frame) for frame in json.loads(raw)] if raw else []


def session_ids(server, player_ids):
    from sqlalchemy import func, select

    from rcon.models import PlayerID, PlayerSession, enter_session
    if not player_ids:
        return {}
    with enter_session() as session:
        rows = session.execute(select(PlayerID.player_id, func.max(PlayerSession.id))
                               .join(PlayerSession, PlayerSession.player_id_id == PlayerID.id)
                               .where(PlayerID.player_id.in_(player_ids), PlayerSession.server_number == server)
                               .group_by(PlayerID.player_id)).all()
        return {p: str(s) for p, s in rows}


def capture(api, server, previous, settings):
    from rcon.utils import MapsHistory, parse_raw_player_info
    state = api.get_gamestate()
    map_data = state["current_map"]
    layer_id = map_data["id"]
    game = api.config.game.value
    raw_sample = api.get_raw_player_snapshot()
    now = raw_sample["captured_at"]
    map_history = MapsHistory().get_current_map() or {}
    # Without a recorder-confirmed round identity, a reconnect cannot safely
    # establish continuity. Expose the map/roster, but don't accumulate evidence.
    round_start = map_history.get("start")
    if (not isinstance(round_start, (int, float)) or round_start > now
            or map_history.get("name") != layer_id or map_history.get("end") is not None):
        round_start = None
    round_id = f"{server}:{game}:{layer_id}:{round_start or 'unknown'}"
    calibration = display_projection(game, map_data['map']['id'], settings["calibrations"])
    scale = calibration["units_per_meter"] if calibration and calibration.get("verified") else None
    adapted = []
    for raw in raw_sample["players"][:200]:
        try:
            p = api.game_profile.player_adapter.adapt(raw)
            detailed = parse_raw_player_info(p, api.config.game)
            lowered = {k.lower(): v for k, v in raw.items()}
            vector = position(lowered.get("worldposition"))
            if game == "hllv" and vietnam_list_only(detailed, vector):
                vector = None
            raw_stats = lowered.get("stats") or {}
            raw_deaths = {k.lower(): v for k, v in raw_stats.items()}.get("deaths")
            deaths_valid = isinstance(raw_deaths, (int, float)) and not isinstance(raw_deaths, bool) and raw_deaths >= 0
            adapted.append({"player_id": detailed["player_id"], "name": detailed["name"],
                            "team": detailed["team"], "unit_name": detailed["unit_name"],
                            "role": detailed["role"], "deaths": detailed["deaths"], "deaths_valid": deaths_valid,
                            "position": vector, "position_valid": vector is not None,
                            "map_position": project(vector, calibration),
                            "position_m": {k: v / scale for k, v in vector.items()} if vector and scale else None})
        except (ValueError, KeyError, TypeError):
            logger.warning("Invalid player payload in tactical sample")
    sessions = session_ids(server, [p["player_id"] for p in adapted])
    old = {p["player_id"]: p for p in (previous or {}).get("players", [])}
    for p in adapted:
        p["session_id"] = sessions.get(p["player_id"])
        prior = old.get(p["player_id"])
        broken = (not previous or previous["round_id"] != round_id
                  or previous.get("calibration") != calibration
                  or segment_break(prior, p, previous["captured_at"], now, scale,
                                   display_only=projection_ready(calibration) and scale is None))
        p["segment_id"] = f"{round_id}:{p['player_id']}:{now}" if broken else prior["segment_id"]
    return {"schema_version": 1, "server_number": server, "game": game, "round_id": round_id,
            "round_start": round_start, "captured_at": now, "map": map_data, "players": adapted,
            "calibration": calibration, "objects": [], "events": [], "signals": [], "detections": [],
            "collector_interval": 2, "collection_seconds": 0,
            "quality": {"valid_positions": sum(p["position_valid"] for p in adapted),
                        "mapped_positions": sum(p["map_position"] is not None for p in adapted),
                        "total_players": len(adapted), "round_confirmed": round_start is not None}}


def attach_event_position(event, frames):
    for frame in reversed(frames):
        if frame["round_id"] != event["round_id"] or not 0 <= event["time"] - frame["captured_at"] <= 3:
            continue
        player = next((p for p in frame["players"] if p["player_id"] == event["victim"]), None)
        attacker = next(
            (p for p in frame["players"] if p["player_id"] == event["attacker"]),
            None,
        )
        if player and player["position_valid"]:
            event.update(position=player["position"], position_m=player["position_m"],
                         position_sample_at=frame["captured_at"], map_position=player["map_position"],
                         victim_role=player["role"], victim_squad=player["unit_name"])
        if attacker:
            event.update(
                attacker_role=attacker.get("role"),
                attacker_squad=attacker.get("unit_name"),
                attacker_position=attacker.get("position"),
                attacker_position_m=attacker.get("position_m"),
                attacker_map_position=attacker.get("map_position"),
                attacker_position_sample_at=(
                    frame["captured_at"] if attacker.get("position_valid") else None
                ),
            )
        if (player and player.get("position_valid")) or attacker:
            return


def active_protected_ids(monitors, players):
    online = {p["player_id"]: p for p in players}
    active = set()
    for monitor in monitors:
        for player_id in monitor.get("aliases", [monitor["player_id"]]):
            player = online.get(player_id)
            if monitor["scope"] == "permanent" or (player and player.get("session_id") and player["session_id"] == monitor.get("session_id")):
                active.add(player_id)
    return active


def owns_lease(lease):
    # Redis itself can be unavailable in the error handler. Never let that
    # bypass backoff or accidentally publish as a second collector.
    try:
        return lease is not None and lease.owned()
    except Exception:
        return False


def run(stop_event=None):
    from rcon.cache_utils import get_redis_client
    from rcon.rcon import get_rcon
    from rcon.utils import LogsHistory, get_server_number
    stop = stop_event or threading.Event()
    red, api, server = get_redis_client(), get_rcon(), int(get_server_number())
    lease = None
    pending, events, recent, first_seen = [], {}, deque(maxlen=512), {}
    previous, cleanup_at, interval = None, 0, 2
    while not stop.is_set():
        started = time.monotonic()
        try:
            if lease is None:
                lease = red.lock(key(server, "collector-lock"), timeout=120, blocking_timeout=0, thread_local=False)
                if not lease.acquire(blocking=False):
                    lease = None
                    stop.wait(5)
                    continue
                previous = read_snapshot(red, server)
                # Restore the rolling window after restart without recreating kills.
                now = time.time()
                pending = read_pending(red, server)
                restored = storage.history(server, now - 900, now) + pending
                restored = sorted({(f["round_id"], f["captured_at"]): f for f in restored}.values(), key=lambda f: f["captured_at"])
                if previous and previous.get("quality", {}).get("round_confirmed"):
                    stored_events, first_seen = storage.round_events(server, previous["round_id"])
                    events.update({event["id"]: event for event in stored_events})
                for frame in restored:
                    events.update({e["id"]: e for e in frame.get("events", [])})
                    for player in frame.get("players", []):
                        if player.get("player_id"):
                            first_seen.setdefault(
                                player["player_id"], frame["captured_at"]
                            )
                recent.extend(restored[-512:])
            lease.extend(120, replace_ttl=True)
            # Retry failed persistence before querying again. A database outage
            # must not produce an unbounded in-memory or Redis history buffer.
            if pending and pending[-1]["captured_at"] - pending[0]["captured_at"] >= 30:
                storage.save_block(server, pending)
                pending = []
                red.delete(key(server, "pending"))
            if time.time() >= cleanup_at:
                storage.cleanup(server)
                cleanup_at = time.time() + 60
            settings = storage.get_settings(server)
            if not settings["enabled"]:
                if pending:
                    storage.save_block(server, pending)
                    pending = []
                red.delete(key(server, "snapshot"), key(server, "pending"))
                previous = None
                stop.wait(5)
                continue
            frame = capture(api, server, previous, settings)
            if previous and frame["captured_at"] <= previous["captured_at"]:
                stop.wait(interval)
                continue
            if previous and previous["round_id"] != frame["round_id"]:
                storage.finish_archive(
                    server, previous["round_id"], previous["captured_at"]
                )
                if pending:
                    storage.save_block(server, pending)
                    pending = []
                events = {}
                first_seen = {}
                recent.clear()
            recent.append(frame)
            now = frame["captured_at"]
            for player in frame["players"]:
                first_seen.setdefault(player["player_id"], now)
            if frame["round_start"] is not None:
                for raw in LogsHistory().iter_range(stop=5000, page_size=250):
                    if float(raw.get("timestamp_ms") or 0) / 1000 < now - 900:
                        continue
                    event = normalize_event(raw, frame["round_id"], frame["round_start"], now)
                    if event and event["id"] not in events:
                        attach_event_position(event, recent)
                        events[event["id"]] = event
                        frame["events"].append(event)
            events = {k: e for k, e in events.items() if e["round_id"] == frame["round_id"]}
            protected = active_protected_ids(settings["monitors"], frame["players"])
            if settings["monitor_enabled"]:
                totals = observed_death_totals(recent, protected, now, frame["round_id"])
                frame["signals"] = evaluate_encounters(events.values(), protected, now, frame["round_id"], totals)
            if settings["detection_enabled"] and frame["quality"]["round_confirmed"]:
                frame["detections"] = evaluate_gameplay_patterns(
                    events.values(), recent, now, frame["round_id"], first_seen,
                    settings["detection_profile"], bool(frame.get("calibration", {}).get("verified")),
                )
                storage.upsert_detections(server, frame["detections"], now)
            duration = time.monotonic() - started
            interval = 10 if duration >= 4 else 5 if duration >= 1.5 else 2
            frame.update(collector_interval=interval, collection_seconds=round(duration, 3))
            if not owns_lease(lease):
                raise RuntimeError("Collector lease lost")
            previous = frame
            # Signals are derived; only store raw evidence once per chunk.
            pending.append({**frame, "signals": [], "detections": []})
            red.set(key(server, "snapshot"), json.dumps(frame, allow_nan=False), ex=120)
            red.set(key(server, "pending"), json.dumps(pending, allow_nan=False), ex=120)
            if pending[-1]["captured_at"] - pending[0]["captured_at"] >= 30:
                storage.save_block(server, pending)
                pending = []
                red.delete(key(server, "pending"))
        except Exception:
            logger.exception("Live-map collector unavailable; last sample remains dated")
            interval = 10
            if not owns_lease(lease):
                lease = None
                pending = []
        stop.wait(max(.1, interval - (time.monotonic() - started)))
    if owns_lease(lease):
        if pending:
            storage.save_block(server, pending)
        lease.release()
