import copy
from types import SimpleNamespace

import pytest
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.live_map import service, storage


@pytest.mark.parametrize("profile", [HLL_PROFILE, HLLV_PROFILE])
def test_real_game_adapters_distinguish_origin_and_missing_positions(profile, monkeypatch):
    history = {"name": "layer", "start": 900, "end": None}
    monkeypatch.setattr("rcon.utils.MapsHistory", lambda: SimpleNamespace(get_current_map=lambda: history))
    monkeypatch.setattr(service, "session_ids", lambda server, ids: {p: "s" for p in ids})
    raw = {"iD": "76561198000000001", "Name": "fixture", "Team": 1, "Role": 1, "Stats": {"Deaths": 0}, "WorldPosition": {"X": 0, "Y": 0, "Z": 0}}
    raw["Platoon"] = "Alfa"
    api = SimpleNamespace(config=SimpleNamespace(game=profile.game), game_profile=profile,
                          get_gamestate=lambda: {"current_map": {"id": "layer", "map": {"id": "map"}}},
                          get_raw_player_snapshot=lambda: {"captured_at": 1000, "players": [raw]})
    settings = copy.deepcopy(storage.DEFAULT_SETTINGS)
    frame = service.capture(api, 1, None, settings)
    assert frame["quality"]["round_confirmed"]
    player = frame["players"][0]
    assert player["position"] == (None if profile is HLLV_PROFILE else {"x": 0, "y": 0, "z": 0})
    assert player["position_valid"] is (profile is HLL_PROFILE)
    assert player["deaths_valid"]
    assert player["map_position"] is None
    raw["WorldPosition"]["Z"] = 1
    assert service.capture(api, 1, frame, settings)["players"][0]["position_valid"]
    raw.pop("Platoon")
    unassigned = service.capture(api, 1, frame, settings)["players"][0]
    assert unassigned["unit_name"] == "unassigned"
    assert unassigned["position_valid"] is (profile is HLL_PROFILE)
    raw.pop("WorldPosition")
    assert not service.capture(api, 1, None, settings)["players"][0]["position_valid"]
    history["name"] = "previous-map"
    assert not service.capture(api, 1, None, settings)["quality"]["round_confirmed"]


@pytest.mark.parametrize("game", ["hllv", "hll"])
def test_stored_frames_keep_the_roster_and_split_placeholder_positions(game):
    from rcon.live_map.domain import normalize_stored_frame, segment_break

    center = {"x": 0, "y": 0, "z": 1}
    point = {"team": "axis", "unit_name": "command", "player_id": "p", "session_id": "s",
             "position_valid": True, "position": center, "position_m": center,
             "map_position": {"x": .5, "y": .5}}
    players = [point, {**point, "position": {**center, "z": 0}},
               {**point, "unit_name": "unassigned"}, {**point, "unit_name": ""},
               {**point, "team": None}, {**point, "team": "unknown"},
               {**point, "unit_name": "alfa", "position": {**center, "x": .001, "z": 0}}]
    frame = normalize_stored_frame({"game": game, "players": players, "quality": {
        "total_players": 7, "valid_positions": 7, "mapped_positions": 7}})
    assert len(frame["players"]) == 7
    expected = 2 if game == "hllv" else 7
    assert frame["quality"] == {"total_players": 7, "valid_positions": expected, "mapped_positions": expected}
    assert frame["players"][0]["map_position"] and frame["players"][-1]["map_position"]
    for hidden in frame["players"][1:-1]:
        if game == "hllv":
            assert not hidden["position_valid"]
            assert hidden["position"] is hidden["position_m"] is hidden["map_position"] is None
            assert segment_break(point, hidden, 1, 2, display_only=True)
            assert segment_break(hidden, point, 2, 3, display_only=True)
        else:
            assert hidden["map_position"] == point["map_position"]


def test_redis_outage_in_lease_check_fails_closed():
    def offline():
        raise ConnectionError("test Redis outage")
    assert not service.owns_lease(SimpleNamespace(owned=offline))
    assert not service.owns_lease(None)


def test_additive_sql_migration_creates_expected_tables_and_indexes():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect
    path = Path(__file__).resolve().parents[1] / "alembic/versions/b7e9d5026a31_live_map.py"
    spec = importlib.util.spec_from_file_location("live_map_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        inspector = inspect(conn)
        assert set(inspector.get_table_names()) == {"tactical_block", "tactical_review", "tactical_settings"}
        indexes = {i["name"] for i in inspector.get_indexes("tactical_block")}
        assert "ix_tactical_block_server_round_time" in indexes
    engine.dispose()


def test_replay_archive_migration_is_additive():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect

    root = Path(__file__).resolve().parents[1] / "alembic/versions"
    migrations = []
    for name in ("b7e9d5026a31_live_map.py", "d2f7a4c9b8e1_live_map_replay_archives.py"):
        spec = importlib.util.spec_from_file_location(name, root / name)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migrations.append(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            for migration in migrations:
                migration.upgrade()
        inspector = inspect(conn)
        assert {"tactical_archive", "tactical_detection"} <= set(inspector.get_table_names())
        assert "ix_tactical_archive_server_expiry" in {
            item["name"] for item in inspector.get_indexes("tactical_archive")
        }
        assert "ix_tactical_detection_server_round" in {
            item["name"] for item in inspector.get_indexes("tactical_detection")
        }
    engine.dispose()
