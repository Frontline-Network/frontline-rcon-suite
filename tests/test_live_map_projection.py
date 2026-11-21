"""A useful display projection must never masquerade as metric evidence."""
import copy
from types import SimpleNamespace
from pathlib import Path

import pytest

from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.game.hll.profile import HLL_PROFILE
from rcon.live_map import service, storage
from rcon.live_map.domain import project, segment_break
from rcon.live_map.projections import HLL_DISPLAY_MAPS, display_projection, projection_ready


def test_field_frame_is_display_only_and_does_not_spread_to_unknown_maps():
    p = display_projection("hllv", "WDEV_B", {})
    assert projection_ready(p)
    assert p["verified"] is False
    assert p["units_per_meter"] is None and p["max_error_m"] is None
    assert project({"x": 0, "y": 0}, p) == {"x": .5, "y": .5}
    assert project({"x": -100000, "y": 100000}, p) == {"x": 0, "y": 1}
    assert project({"x": 100001, "y": 0}, p) is None
    assert display_projection("hll", "WDEV_B", {}) is None
    for map_id in ("unknown", "wdev_g"):
        assert display_projection("hllv", map_id, {}) is None
    assert display_projection("hllv", "wdev_f", {})["quality"] == "estimated"
    assert not projection_ready({"verified": False})


@pytest.mark.parametrize("map_id", [f"wdev_{letter}" for letter in "abcdef"])
def test_all_six_vietnam_maps_have_explicit_nonmetric_previews(map_id):
    p = display_projection("hllv", map_id, {})
    assert projection_ready(p) and p["quality"] == "estimated"
    assert not p["verified"]
    assert p["units_per_meter"] is None and p["max_error_m"] is None
    assert p["map_id"] == map_id and p["source"]
    assert project({"x": 20000, "y": -40000}, p) == {"x": .6, "y": .3}
    assert display_projection("hll", map_id, {}) is None


def test_existing_operator_calibration_is_preserved_and_not_mutated():
    configured = {"hllv:wdev_b": {"verified": True, "matrix": [1, 0, 0, 0, 1, 0]}}
    result = display_projection("hllv", "wdev_b", configured)
    assert result == configured["hllv:wdev_b"]
    result["matrix"][0] = 2
    assert configured["hllv:wdev_b"]["matrix"][0] == 1
    assert display_projection("hllv", "wdev_b", {"hllv:wdev_b": {"verified": False}}) == {"verified": False}


def test_hll_display_allowlist_matches_all_shipped_hll_tactical_images():
    images = Path(__file__).resolve().parents[1] / "assets/images/tac-maps"
    assert HLL_DISPLAY_MAPS == {p.stem for p in images.glob("*.webp") if not p.stem.startswith("wdev_")}


@pytest.mark.parametrize("map_id", sorted(HLL_DISPLAY_MAPS))
def test_hll_display_enabled_but_does_not_invent_metric_verification(map_id):
    p = display_projection("hll", map_id.upper(), {})
    assert projection_ready(p) and p["quality"] == "estimated"
    assert p["verified"] is False
    assert p["units_per_meter"] is None and p["max_error_m"] is None
    assert p["map_id"] == map_id and "assumed" in p["source"]
    assert project({"x": 0, "y": 0}, p) == {"x": .5, "y": .5}
    assert project({"x": -100000, "y": 100000}, p) == {"x": 0, "y": 1}
    assert project({"x": 100001, "y": 0}, p) is None
    assert display_projection("hllv", map_id, {}) is None
    assert display_projection("other", map_id, {}) is None
    for custom in ({"verified": False}, {"verified": True, "matrix": [1, 0, 0, 0, 1, 0]}):
        assert display_projection("hll", map_id, {f"hll:{map_id}": custom}) == custom


def test_unknown_hll_maps_stay_unmapped():
    assert display_projection("hll", "future_map", {}) is None


@pytest.mark.parametrize("world, grid", [
    ({"x": 12820.8123, "y": -35222.6192}, "F4"),
    ({"x": 21121.2846, "y": -50182.5628}, "G3"),
    ({"x": 22224.9575, "y": -27796.6707}, "G4"),
])
def test_quang_ngai_stationary_samples_match_observed_in_game_cells(world, grid):
    # Grid agreement is explicitly NOT an independent <=10 metre acceptance.
    uv = project(world, display_projection("hllv", "wdev_b", {}))
    assert chr(65 + int(uv["x"] * 10)) + str(1 + int(uv["y"] * 10)) == grid


def test_preview_traces_cut_missing_positions_deaths_jumps_and_time_gaps():
    a = {"position_valid": True, "map_position": {"x": .5, "y": .5},
         "session_id": "s", "team": "allies", "deaths": 0}
    b = {**a, "map_position": {"x": .51, "y": .51}}
    assert not segment_break(a, b, 0, 2, display_only=True)
    assert segment_break(a, b, 0, 2)  # unknown projection still cannot join traces
    for change in ({"map_position": None}, {"deaths": 1}, {"session_id": "new"},
                   {"team": "axis"}, {"map_position": {"x": .9, "y": .9}}):
        assert segment_break(a, {**b, **change}, 0, 2, display_only=True)
    assert segment_break(a, b, 0, 13, display_only=True)


@pytest.mark.parametrize("profile,map_id", [(HLLV_PROFILE, f"WDEV_{letter}") for letter in "ABCDEF"]
                         + [(HLL_PROFILE, map_id) for map_id in sorted(HLL_DISPLAY_MAPS)])
def test_bulk_capture_maps_100_players_without_metric_monitor_positions(monkeypatch, profile, map_id):
    monkeypatch.setattr("rcon.utils.MapsHistory", lambda: SimpleNamespace(get_current_map=lambda: {"name": "layer", "start": 900, "end": None}))
    monkeypatch.setattr(service, "session_ids", lambda server, ids: {p: "s" for p in ids})
    raw = [{"iD": str(76561198000000000 + i), "Name": f"fixture-{i}", "Team": i % 2 + 1,
            "Platoon": "Alfa", "Role": 1, "Stats": {"Deaths": 0},
            "WorldPosition": {"X": i * 100, "Y": -20000, "Z": 0}} for i in range(100)]
    calls = []
    def sample():
        calls.append(True)
        return {"captured_at": 1000 + 2 * len(calls), "players": raw}
    api = SimpleNamespace(config=SimpleNamespace(game=profile.game), game_profile=profile,
        get_gamestate=lambda: {"current_map": {"id": "layer", "map": {"id": map_id}}},
        get_raw_player_snapshot=sample)
    settings = copy.deepcopy(storage.DEFAULT_SETTINGS)
    frame = service.capture(api, 3, None, settings)
    assert len(calls) == 1 and frame["quality"]["mapped_positions"] == 100
    assert all(p["map_position"] is not None and p["position_m"] is None for p in frame["players"])
    second = service.capture(api, 3, frame, settings)
    assert second["players"][0]["segment_id"] == frame["players"][0]["segment_id"]
    assert not settings["calibrations"]
