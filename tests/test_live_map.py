import copy
import json
import math

import pytest

from rcon.live_map.domain import (
    calibrate,
    evaluate_encounters,
    evaluate_gameplay_patterns,
    normalize_event,
    observed_death_totals,
    position,
    project,
    redact_positions,
    segment_break,
)
from rcon.live_map.service import active_protected_ids, attach_event_position
from rcon.live_map.storage import pack, unpack


def calibration():
    anchors = [{"x": 0, "y": 0, "u": 0, "v": 0}, {"x": 200000, "y": 0, "u": 1, "v": 0}, {"x": 0, "y": 200000, "u": 0, "v": 1}]
    checks = [{"x": 200000, "y": 200000, "u": 1, "v": 1}, {"x": 100000, "y": 100000, "u": .5, "v": .5}]
    return anchors, checks


@pytest.mark.parametrize("value", [None, {}, {"x": 0, "y": 0}, {"x": True, "y": 0, "z": 0}, {"x": math.nan, "y": 1, "z": 0}, {"x": math.inf, "y": 0, "z": 0}, {"x": "unknown", "y": 0, "z": 0}])
def test_missing_or_invalid_position_does_not_become_origin(value):
    assert position(value) is None


def test_true_origin_and_hllv_case_normalize_without_becoming_missing():
    assert position({"X": "0", "Y": 0, "Z": 0}) == {"x": 0., "y": 0., "z": 0.}


def test_calibration_uses_independent_checks_and_projects_points():
    anchors, checks = calibration()
    result = calibrate(anchors, checks, 100, "synthetic control fixture")
    assert result["max_error_m"] == pytest.approx(0)
    assert project({"x": 100000, "y": 100000}, result) == {"x": .5, "y": .5}
    assert project({"x": 200001, "y": 0}, result) is None
    assert project({"x": 1, "y": 1}, {"verified": False}) is None
    checks[0]["u"] = .9
    with pytest.raises(ValueError, match="zehn Meter"):
        calibrate(anchors, checks, 100, "bad independent check")
    with pytest.raises(ValueError, match="unabhängig"):
        calibrate(anchors, [anchors[0], checks[1]], 100, "duplicate")


def event(index, attacker="a", victim="v", located=True):
    return {"id": str(index), "round_id": "round", "time": 1000 + index * 10,
            "attacker": attacker, "victim": victim, "teamkill": False,
            "position_m": {"x": index * 100., "y": 0} if located else None}


def test_repetitions_are_explainable_and_deduplicated():
    kills = [event(i) for i in range(3)]
    result = evaluate_encounters(kills + kills, {"v"}, 1100, "round")
    assert result[0]["kind"] == "repeated"
    assert result[0]["count"] == 3
    assert len(result[0]["events"]) == 3


def test_review_requires_all_conditions_including_valid_distinct_locations():
    kills = [event(i) for i in range(4)] + [event(5, attacker="other")]
    s = evaluate_encounters(kills, {"v"}, 1100, "round", {"v": 5})[0]
    assert s["kind"] == "review"
    assert s["share"] == .8
    assert s["total_deaths"] == 5
    for e in kills:
        e["position_m"] = None
    assert evaluate_encounters(kills, {"v"}, 1100, "round")[0]["kind"] == "repeated"
    for e in kills:
        e["position_m"] = {"x": 0, "y": 0}
    assert evaluate_encounters(kills, {"v"}, 1100, "round")[0]["kind"] == "repeated"


def test_normal_duels_teamkills_old_events_and_rounds_do_not_escalate():
    kills = [event(i) for i in range(3)] + [event(5, attacker="v", victim="a")]
    old = event(-100)
    other_round = {**event(6), "round_id": "other"}
    tk = {**event(7), "teamkill": True}
    s = evaluate_encounters(kills + [old, other_round, tk], {"v"}, 1100, "round")[0]
    assert s["count"] == 3 and s["counterkills"] == 1 and s["total_deaths"] == 4
    assert evaluate_encounters(kills, set(), 1100, "round") == []


def test_highlight_requires_sixty_percent_and_five_deaths():
    kills = [event(i) for i in range(4)]
    assert evaluate_encounters(kills, {"v"}, 1100, "round")[0]["kind"] == "repeated"
    kills += [event(i, attacker=f"other-{i}") for i in range(4, 8)]
    assert evaluate_encounters(kills, {"v"}, 1100, "round", {"v": 8})[0]["kind"] == "repeated"


def test_missing_death_counters_cannot_artificially_raise_kill_share():
    kills = [event(i) for i in range(4)] + [event(5, attacker="other")]
    assert evaluate_encounters(kills, {"v"}, 1100, "round")[0]["kind"] == "repeated"
    assert evaluate_encounters(kills, {"v"}, 1100, "round", {"v": 10})[0]["share"] == .4
    assert evaluate_encounters(kills, {"v"}, 1100, "round", {"v": 10})[0]["kind"] == "repeated"


def test_death_counter_coverage_rejects_gaps_reconnects_and_resets():
    frames = [{"round_id": "r", "captured_at": t, "players": [{"player_id": "v", "deaths": t // 100, "deaths_valid": True, "session_id": "s"}]} for t in range(0, 902, 2)]
    assert observed_death_totals(frames, {"v"}, 900, "r") == {"v": 9}
    assert observed_death_totals(frames[1:], {"v"}, 900, "r") == {}
    assert observed_death_totals(frames[:3] + frames[20:], {"v"}, 900, "r") == {}
    frames[30]["players"][0]["session_id"] = "reconnect"
    assert observed_death_totals(frames, {"v"}, 900, "r") == {}


def test_log_normalization_excludes_unattributed_object_destruction():
    log = {"action": "KILL", "timestamp_ms": 1010000, "player_id_1": "a", "player_id_2": "v"}
    assert normalize_event(log, "r", 1000, 1020)["victim"] == "v"
    assert normalize_event(log, "r", 1020, 1030) is None
    assert normalize_event({**log, "action": "GARRISON DISAPPEARED"}, "r", 1000, 1020) is None
    assert normalize_event({**log, "raw": "[100 ms] KILL"}, "r", 1000, 1020)["id"] == normalize_event({**log, "raw": "[200 ms] KILL"}, "r", 1000, 1020)["id"]


def test_trajectories_break_on_death_session_team_jump_or_missing_samples():
    p = {"position_valid": True, "position": {"x": 0, "y": 0}, "session_id": "s", "team": "allies", "deaths": 1}
    q = {**p, "position": {"x": 1000, "y": 0}}
    assert not segment_break(p, q, 0, 2, 100)
    for change in ({"position_valid": False}, {"session_id": "new"}, {"deaths": 2}, {"team": "axis"}, {"position": {"x": 100000, "y": 0}}):
        assert segment_break(p, {**q, **change}, 0, 2, 100)
    assert segment_break(p, q, 0, 15, 100)
    assert segment_break(p, q, 0, 2, None)


def test_kill_location_is_never_borrowed_from_future_or_old_measurement():
    e = event(0)
    e.update(position=None, position_m=None)
    p = {"player_id": "v", "position_valid": True, "position": {"x": 1, "y": 1}, "position_m": {"x": 1, "y": 1}, "map_position": {"x": .1, "y": .1}, "role": "rifleman", "unit_name": "able"}
    frames = [{"round_id": "round", "captured_at": 996, "players": [p]}, {"round_id": "round", "captured_at": 1001, "players": [p]}]
    attach_event_position(e, frames)
    assert e["position"] is None
    frames.insert(1, {"round_id": "round", "captured_at": 999, "players": [p]})
    attach_event_position(e, frames)
    assert e["position_sample_at"] == 999


def test_session_monitor_cannot_silently_survive_reconnect():
    monitors = [{"player_id": "v", "scope": "session", "session_id": "1", "aliases": ["v"]}]
    assert active_protected_ids(monitors, [{"player_id": "v", "session_id": "1"}]) == {"v"}
    assert not active_protected_ids(monitors, [{"player_id": "v", "session_id": "2"}])
    assert not active_protected_ids(monitors, [])
    monitors[0]["scope"] = "permanent"
    assert active_protected_ids(monitors, []) == {"v"}


def test_nested_and_encoded_legacy_data_cannot_leak_coordinates():
    payload = {"players": [{"name": "keep", "world_position": {"x": 10}}],
               "raw": json.dumps({"WorldPosition": {"X": 5}, "name": "keep"}),
               "objects": {"garrisons": [{"position": {"x": 1}}]}}
    original = copy.deepcopy(payload)
    result = redact_positions(payload)
    assert result["players"] == [{"name": "keep"}]
    assert json.loads(result["raw"]) == {"name": "keep"}
    assert result["objects"] == {}
    assert payload == original


def test_compressed_blocks_preserve_100_players_without_individual_rows():
    data = [{"captured_at": t, "players": [{"player_id": str(p), "position": {"x": p * 100, "y": t, "z": 0}} for p in range(100)]} for t in range(0, 32, 2)]
    compressed = pack(data)
    assert unpack(compressed) == data
    assert len(compressed) < len(json.dumps(data)) / 5


def gameplay_event(index, now, weapon="M1 GARAND"):
    return {
        "id": f"kill-{index}",
        "round_id": "round",
        "time": now - 100 + index * 4,
        "attacker": "player",
        "attacker_name": "Player",
        "victim": f"victim-{index}",
        "victim_name": f"Victim {index}",
        "weapon": weapon,
        "teamkill": False,
    }


def test_kill_rate_and_infantry_burst_create_explainable_review_not_action():
    from rcon.live_map.storage import DETECTION_PROFILE

    now = 2000.0
    events = [gameplay_event(index, now) for index in range(25)]
    frames = [{"round_id": "round", "captured_at": now, "players": [{"player_id": "player", "name": "Player"}]}]
    result = evaluate_gameplay_patterns(
        events + copy.deepcopy(events),
        frames,
        now,
        "round",
        {"player": now - 600},
        DETECTION_PROFILE,
        False,
    )
    assert len(result) == 1
    assert result[0]["severity"] == "review"
    assert {item["kind"] for item in result[0]["signals"]} == {"kill_rate", "kill_burst"}
    assert result[0]["metrics"]["kills"] == 25
    assert "action" not in result[0]


def test_special_weapon_multikill_alone_does_not_create_hint():
    from rcon.live_map.storage import DETECTION_PROFILE

    now = 2000.0
    events = [
        gameplay_event(index, now, "155MM HOWITZER [M114]")
        for index in range(10)
    ]
    assert evaluate_gameplay_patterns(
        events, [], now, "round", {"player": now - 60}, DETECTION_PROFILE, False
    ) == []
    grenades = [
        gameplay_event(index, now, "MK2 GRENADE") for index in range(30)
    ]
    assert evaluate_gameplay_patterns(
        grenades,
        [],
        now,
        "round",
        {"player": now - 60},
        DETECTION_PROFILE,
        False,
    ) == []
    unknown = [
        gameplay_event(index, now, "FUTURE UNKNOWN EXPLOSIVE")
        for index in range(30)
    ]
    assert evaluate_gameplay_patterns(
        unknown,
        [],
        now,
        "round",
        {"player": now - 60},
        DETECTION_PROFILE,
        False,
    ) == []


def test_two_consecutive_metric_jumps_remain_diagnostic_after_normal_movement():
    from rcon.live_map.storage import DETECTION_PROFILE

    def sample(at, x):
        return {
            "round_id": "round",
            "captured_at": at,
            "players": [{
                "player_id": "player",
                "name": "Player",
                "session_id": "session",
                "team": "allies",
                "deaths": 0,
                "position_m": {"x": x, "y": 0},
                "map_position": {"x": x / 1000, "y": 0.5},
            }],
        }

    frames = [sample(0, 0), sample(2, 120), sample(4, 240), sample(6, 242)]
    result = evaluate_gameplay_patterns(
        [], frames, 6, "round", {"player": 0}, DETECTION_PROFILE, True
    )
    assert result[0]["severity"] == "observation"
    assert result[0]["signals"][0]["kind"] == "movement_anomaly"
    assert evaluate_gameplay_patterns(
        [], frames, 6, "round", {"player": 0}, DETECTION_PROFILE, False
    ) == []
