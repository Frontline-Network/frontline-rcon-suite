import copy
from types import SimpleNamespace

import pytest
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.live_map import service, storage


@pytest.mark.parametrize("profile", [HLL_PROFILE, HLLV_PROFILE])
def test_real_game_adapters_preserve_valid_origin_and_missing_positions(profile, monkeypatch):
    history = {"name": "layer", "start": 900, "end": None}
    monkeypatch.setattr("rcon.utils.MapsHistory", lambda: SimpleNamespace(get_current_map=lambda: history))
    monkeypatch.setattr(service, "session_ids", lambda server, ids: {p: "s" for p in ids})
    raw = {"iD": "76561198000000001", "Name": "fixture", "Team": 1, "Role": 1, "Stats": {"Deaths": 0}, "WorldPosition": {"X": 0, "Y": 0, "Z": 0}}
    api = SimpleNamespace(config=SimpleNamespace(game=profile.game), game_profile=profile,
                          get_gamestate=lambda: {"current_map": {"id": "layer", "map": {"id": "map"}}},
                          get_raw_player_snapshot=lambda: {"captured_at": 1000, "players": [raw]})
    settings = copy.deepcopy(storage.DEFAULT_SETTINGS)
    frame = service.capture(api, 1, None, settings)
    assert frame["quality"]["round_confirmed"]
    player = frame["players"][0]
    assert player["position"] == {"x": 0, "y": 0, "z": 0}
    assert player["position_valid"] and player["deaths_valid"]
    assert player["map_position"] is None
    raw.pop("WorldPosition")
    assert not service.capture(api, 1, None, settings)["players"][0]["position_valid"]
    history["name"] = "previous-map"
    assert not service.capture(api, 1, None, settings)["quality"]["round_confirmed"]


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
