from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from rcon import population as p
from rcon.population_models import PopulationSample, SeedingSession
from rcon.user_config.population_history import PopulationHistoryUserConfig as Config

NOW = 1800000000  # Aligned to minute/hour; UTC timestamps stay deterministic.


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (PopulationSample, SeedingSession):
        model.__table__.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def session():
        with factory.begin() as db:
            yield db

    monkeypatch.setattr(p, "enter_session", session)
    monkeypatch.setattr(p.time, "time", lambda: NOW + 86400)
    yield session
    engine.dispose()


def record(count, at=NOW, server=1, interval=30):
    rcon = Mock()
    if isinstance(count, Exception):
        rcon.get_slots.side_effect = count
    else:
        rcon.get_slots.return_value = {"current_players": count, "max_players": 100}
    rcon.get_map.return_value = "foy_warfare"
    return p.record_sample(
        rcon, server, Config(interval_seconds=interval), clock=lambda: at + 1
    )


def test_zero_failure_missing_and_server_isolation(database):
    record(0)
    record(TimeoutError("private diagnostic"), NOW + 30)
    record(80, NOW + 120)
    record(99, NOW, server=2)
    result = p.history(1, NOW, NOW + 180, "1m")
    first, missing, last = result["points"]
    assert (first["mean"], first["sample_count"], first["failed_sample_count"]) == (
        0,
        1,
        1,
    )
    assert first["sampling_coverage"] == 0.5
    assert missing["mean"] is None and missing["sampling_coverage"] == 0
    assert last["mean"] == 80
    assert result["sampling_coverage"] == pytest.approx(1 / 3)
    assert result["first_available_at"] == p.utc(NOW)
    raw = p.history(1, NOW, NOW + 180, "raw")["points"]
    assert raw[1]["player_count"] is None and raw[1]["status"] == "rcon_error"
    assert "private diagnostic" not in str(result) + str(raw)


def test_restart_duplicate_interval_change_and_recovery(database):
    assert record(10)
    assert not record(20)
    assert not record(20, NOW + 15, interval=15)
    assert record(TimeoutError(), NOW + 30)
    assert record(40, NOW + 60)
    point = p.history(1, NOW, NOW + 120, "5m")["points"][0]
    assert (point["mean"], point["min"], point["max"]) == (25, 10, 40)
    assert point["sample_count"] == 2 and point["failed_sample_count"] == 1


def test_lock_loser_does_not_query_rcon(database, monkeypatch):
    monkeypatch.setattr(p, "_lock", lambda *a, **k: False)
    rcon = Mock()
    assert not p.record_sample(rcon, 1, Config(), clock=lambda: NOW)
    rcon.get_slots.assert_not_called()


def test_partial_metadata_does_not_erase_valid_counts(database):
    rcon = Mock()
    rcon.get_slots.return_value = {"current_players": 25, "max_players": 100}
    rcon.get_map.side_effect = TimeoutError()
    p.record_sample(rcon, 1, Config(), clock=lambda: NOW + 1)
    point = p.history(1, NOW, NOW + 30, "raw")["points"][0]
    assert point["status"] == "ok" and point["map"] is None
    assert point["player_count"] == 25


@pytest.mark.parametrize("count", [-1, 101, True, "12", None])
def test_invalid_counts_are_failures(database, count):
    record(count)
    assert p.history(1, NOW, NOW + 30, "raw")["points"][0]["status"] == "rcon_error"


def test_slow_rcon_response_is_not_assigned_to_an_old_slot(database):
    rcon = Mock()
    rcon.get_slots.return_value = {"current_players": 10, "max_players": 100}
    p.record_sample(rcon, 1, Config(), clock=Mock(side_effect=[NOW + 1, NOW + 31]))
    assert p.history(1, NOW, NOW + 30, "raw")["points"][0]["player_count"] is None


def test_raw_pagination_half_open_bounds_and_timezone(database):
    for i in range(4):
        record(i, NOW + 30 * i)
    page = p.history(1, NOW, NOW + 90, "raw", limit=2)
    assert len(page["points"]) == 2 and page["next_from"] == p.utc(NOW + 60)
    tail = p.history(1, page["next_from"], NOW + 90, "raw", limit=2)
    assert [row["player_count"] for row in tail["points"]] == [2]
    assert tail["next_from"] is None
    assert p.timestamp("2026-09-26T02:00:00+02:00") == p.timestamp(
        "2026-09-26T00:00:00Z"
    )


@pytest.mark.parametrize("value", ["2026-09-26", "nan", "inf", "-1", "bad"])
def test_bad_timestamps_are_rejected(value):
    with pytest.raises(ValueError):
        p.timestamp(value)


def test_limits_and_empty_history(database):
    assert p.history(1, NOW, NOW + 60, "1m")["points"][0]["mean"] is None
    for start, end, resolution, limit in [
        (NOW, NOW, "raw", 5),
        (NOW, NOW + 32 * 86400, "raw", 5),
        (NOW, NOW + 600, "1m", 5),
        (NOW, NOW + 60, "bad", 5),
        (NOW, NOW + 60, "raw", 5001),
    ]:
        with pytest.raises(ValueError):
            p.history(1, start, end, resolution, limit)


def test_pruning_is_server_scoped_and_does_not_remove_session_markers(database):
    record(10, NOW)
    record(20, NOW, server=2)
    marker = p.mark_seeding(1, "start", uuid4(), "operator", now=NOW)
    p.prune(1, 1, now=NOW + 86401)
    assert not p.history(1, NOW, NOW + 60, "raw")["points"]
    assert p.history(2, NOW, NOW + 60, "raw")["points"]
    assert p.seeding_history(1, NOW, NOW + 60)[0]["id"] == marker["id"]


def test_seeding_markers_are_retry_safe_and_never_infer_seeder_counts(database):
    session_id = uuid4()
    marker = p.mark_seeding(1, "start", session_id, "operator", now=NOW)
    assert marker["seeder_count"] is None
    assert p.mark_seeding(1, "start", session_id, "operator", now=NOW + 5) == marker
    with pytest.raises(ValueError):
        p.mark_seeding(1, "start", uuid4(), "operator", now=NOW)
    with pytest.raises(ValueError):
        p.mark_seeding(2, "end", session_id, "operator", now=NOW + 10)
    ended = p.mark_seeding(1, "end", session_id, "operator", now=NOW + 300)
    assert p.mark_seeding(1, "end", session_id, "operator", now=NOW + 600) == ended
    assert p.seeding_history(1, NOW + 10, NOW + 40) == [ended]
    assert not p.seeding_history(2, NOW, NOW + 600)
    assert (
        p.mark_seeding(1, "start", uuid4(), "operator", 8, now=NOW + 310)[
            "seeder_count"
        ]
        == 8
    )


def test_session_does_not_hide_database_failure(monkeypatch):
    from sqlalchemy.exc import ProgrammingError

    factory = Mock()
    factory.begin.side_effect = ProgrammingError(
        "SELECT", {}, Exception("missing table")
    )
    monkeypatch.setattr(p, "get_session_maker", lambda: factory)
    monkeypatch.setattr(p.time, "time", lambda: NOW + 86400)
    with pytest.raises(ProgrammingError):
        p.history(1, NOW, NOW + 60)


def test_migration_roundtrip_preserves_legacy_tables():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, text

    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/f4b9c2d6e310_population_history.py"
    )
    spec = importlib.util.spec_from_file_location("population_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE server_counts (id INTEGER PRIMARY KEY)"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            assert set(inspect(conn).get_table_names()) == {
                "server_counts",
                "population_samples",
                "population_seeding_sessions",
            }
            assert {
                c["name"] for c in inspect(conn).get_columns("population_samples")
            } == set(PopulationSample.__table__.columns.keys())
            migration.downgrade()
            assert inspect(conn).get_table_names() == ["server_counts"]
    engine.dispose()
