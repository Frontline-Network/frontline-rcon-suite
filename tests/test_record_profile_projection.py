"""Player-record summaries preserve the full projection without loading its histories."""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from rcon import models, player_history
from rcon.models import (
    Blacklist, BlacklistRecord, PlayerAccount, PlayerFlag, PlayerID, PlayerName,
    PlayersAction, PlayerSession, PlayerSoldier, PlayerVIP, SteamInfo, WatchList,
)
from rcon.types import BlacklistSyncMethod


@compiles(JSONB, "sqlite")
def sqlite_json(_element, _compiler, **_kwargs):
    return "JSON"


NOW = datetime(2026, 10, 25, 2, 30, 0, 500000, tzinfo=timezone.utc)
LOCAL_NOW = NOW.astimezone().replace(tzinfo=None)


@pytest.fixture(params=["sqlite", "postgresql"])
def record_database(monkeypatch, request):
    root = None
    schema_name = None
    if request.param == "postgresql":
        dsn = os.environ.get("TEST_POSTGRES_DSN")
        if not dsn:
            pytest.skip("requires disposable PostgreSQL")
        root = create_engine(dsn)
        schema_name = "record_projection_" + uuid4().hex
        with root.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema_name}"})
    else:
        engine = create_engine("sqlite://")
    with monkeypatch.context() as schema:
        schema.setattr(PlayersAction.__table__.c.by, "nullable", True)
        for model in (
            PlayerID, PlayerName, PlayerAccount, PlayerSoldier, PlayerSession,
            PlayersAction, Blacklist, BlacklistRecord, PlayerFlag, PlayerVIP, SteamInfo, WatchList,
        ):
            model.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def enter():
        with maker() as session:
            yield session

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else LOCAL_NOW

    monkeypatch.setattr(player_history, "enter_session", enter)
    # Replace only this module's clock. Altering the stdlib datetime module
    # changes SQLite's isinstance checks and can bind original datetime values
    # as plain dates, silently discarding their time components.
    monkeypatch.setattr(player_history, "datetime", SimpleNamespace(
        **{**vars(player_history.datetime), "datetime": FrozenDatetime},
    ))
    monkeypatch.setattr(models, "datetime", FrozenDatetime)
    monkeypatch.setenv("SERVER_NUMBER", "3")
    try:
        yield engine, maker
    finally:
        engine.dispose()
        if root is not None:
            with root.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
            root.dispose()


def make_player(session, player_id="synthetic-player", *, steam_id=None):
    player = PlayerID(player_id=player_id, steam_id=steam_id, created=LOCAL_NOW - timedelta(days=10))
    player.names = [PlayerName(name=player_id, last_seen=LOCAL_NOW)]
    player.soldier = PlayerSoldier(name=player_id, platform="ps5", level=55)
    player.account = PlayerAccount(name="Selected display name", lang="fr", country="FR")
    session.add(player)
    session.flush()
    return player


def history_row(player, *, created=None, start=None, end=None, server=3, start_us=None, end_us=None):
    return PlayerSession(player_id_id=player.id, created=created or LOCAL_NOW - timedelta(days=1),
                         start=start, end=end, server_number=server,
                         start_event_us=start_us, end_event_us=end_us)


def get_projection(*, compact=False, **kwargs):
    return player_history.get_players_by_appearance(
        compact=compact, observed_at=NOW, online_now_ids=set(), **kwargs,
    )


@pytest.mark.parametrize("scenario", [
    "empty", "fractional", "fractional_rounding_boundary", "varied_fractional_magnitudes",
    "dst_and_negative", "local_before_closed_remote",
    "newer_active_remote", "ended_local_hides_old_open", "absolute_order",
    "id_tie", "missing_start", "future_start", "absolute_end_without_wall_end",
])
def test_record_summary_matches_full_session_semantics(record_database, scenario):
    _engine, maker = record_database
    with maker.begin() as session:
        player = make_player(session)
        local_start = LOCAL_NOW - timedelta(hours=1)
        remote_start = LOCAL_NOW - timedelta(minutes=5)
        epoch = int(NOW.timestamp() * 1_000_000)
        if scenario == "fractional":
            # Truncating each duration would incorrectly produce zero total seconds.
            for i in range(20):
                start = LOCAL_NOW - timedelta(days=i+1)
                session.add(history_row(player, created=start, start=start, end=start+timedelta(microseconds=100001)))
        elif scenario in ("fractional_rounding_boundary", "varied_fractional_magnitudes"):
            durations = [100000] * 10 if scenario == "fractional_rounding_boundary" else [100000, 86400_100001, 1] * 40
            for i, duration in enumerate(durations):
                start = LOCAL_NOW - timedelta(days=i+1)
                session.add(history_row(player, created=start, start=start, end=start+timedelta(microseconds=duration)))
        elif scenario == "dst_and_negative":
            session.add_all([
                history_row(player, start=LOCAL_NOW, end=LOCAL_NOW-timedelta(hours=1)),
                history_row(player, start=LOCAL_NOW, end=LOCAL_NOW-timedelta(hours=1),
                            start_us=epoch-3600_000_000, end_us=epoch),
                history_row(player, start_us=epoch, end_us=epoch-1),
            ])
        elif scenario in ("local_before_closed_remote", "newer_active_remote"):
            session.add_all([
                history_row(player, created=local_start, start=local_start, start_us=epoch-3600_000_000),
                history_row(player, server=4, created=remote_start, start=remote_start,
                            end=LOCAL_NOW-timedelta(minutes=3) if scenario == "local_before_closed_remote" else None,
                            start_us=epoch-300_000_000,
                            end_us=epoch-180_000_000 if scenario == "local_before_closed_remote" else None),
            ])
        elif scenario == "ended_local_hides_old_open":
            session.add_all([
                history_row(player, start=local_start, created=local_start),
                history_row(player, start=remote_start, created=remote_start, end=LOCAL_NOW),
            ])
        elif scenario == "absolute_order":
            session.add_all([
                history_row(player, created=LOCAL_NOW, start=local_start,
                            start_us=epoch-3600_000_000, end_us=epoch-3500_000_000),
                history_row(player, created=local_start, start=remote_start, start_us=epoch-300_000_000),
            ])
        elif scenario == "id_tie":
            session.add_all([
                history_row(player, created=LOCAL_NOW, start=local_start, start_us=epoch-300_000_000),
                history_row(player, created=LOCAL_NOW, start=local_start,
                            start_us=epoch-300_000_000, end_us=epoch-100_000_000),
            ])
        elif scenario == "missing_start":
            session.add(history_row(player, created=local_start))
        elif scenario == "future_start":
            session.add(history_row(player, start=LOCAL_NOW+timedelta(hours=1), start_us=epoch+3600_000_000))
        elif scenario == "absolute_end_without_wall_end":
            session.add(history_row(player, start=local_start, start_us=epoch-3600_000_000, end_us=epoch))

    full = get_projection()["players"][0]
    summary = get_projection(compact=True)["players"][0]
    expected = {
        "empty": 0, "fractional": 2, "fractional_rounding_boundary": 0,
        "dst_and_negative": 3600, "local_before_closed_remote": 3720,
        "newer_active_remote": 300, "ended_local_hides_old_open": 300,
        "absolute_order": 400, "id_tie": 200, "missing_start": 0,
        "future_start": 0, "absolute_end_without_wall_end": 3600,
    }
    if scenario in expected:
        assert full["total_playtime_seconds"] == expected[scenario], scenario
    assert summary == {key: value for key, value in full.items() if key not in ("sessions", "received_actions")}, scenario
    assert "sessions" not in summary and "received_actions" not in summary


def test_record_summary_preserves_counts_and_identity_status(record_database):
    _engine, maker = record_database
    with maker.begin() as session:
        classic = make_player(session, "76561198000000000")
        player = make_player(session, "0123456789abcdef0123456789abcdef", steam_id=classic.player_id)
        player.flags = [PlayerFlag(flag="Observe")]
        player.watchlist = WatchList(is_watched=True, reason="Synthetic", by="Admin", count=2)
        player.steaminfo = SteamInfo(profile={"avatar":"synthetic"}, bans={}, country="DE", updated=LOCAL_NOW)
        lists = [Blacklist(name="local", sync=BlacklistSyncMethod.KICK_ONLY, servers=4),
                 Blacklist(name="other", sync=BlacklistSyncMethod.KICK_ONLY, servers=8)]
        session.add_all(lists)
        session.flush()
        session.add_all([
            BlacklistRecord(player_id_id=player.id, blacklist_id=lists[0].id, reason="local", admin_name="Test"),
            BlacklistRecord(player_id_id=classic.id, blacklist_id=lists[1].id, reason="linked", admin_name="Test"),
            PlayerVIP(player_id_id=player.id, server_number=3, expiration=NOW+timedelta(days=1)),
        ])
        for kind in ("PUNISH", "PUNISH", "KICK", "TEMPBAN", "PERMABAN", "MESSAGE", "", "unknown"):
            session.add(PlayersAction(player_id_id=player.id, action_type=kind, reason="Synthetic", by=None, time=LOCAL_NOW))
    full = get_projection()
    summary = get_projection(compact="true")
    assert [{k:v for k,v in p.items() if k not in ("sessions","received_actions")} for p in full["players"]] == summary["players"]
    profile = next(p for p in summary["players"] if p["steam_id"])
    assert profile["penalty_count"] == {"PUNISH":2,"KICK":1,"TEMPBAN":1,"PERMABAN":1}
    assert profile["is_watched"] and profile["is_blacklisted"] and profile["is_vip"]
    assert profile["identity"]["linked_accounts"][0]["player_id"] == classic.player_id


def test_summary_streams_columns_and_never_loads_full_history_models(record_database, monkeypatch):
    engine, maker = record_database
    with maker.begin() as session:
        player = make_player(session)
        session.add_all(history_row(player, start=LOCAL_NOW-timedelta(seconds=i+1), end=LOCAL_NOW-timedelta(seconds=i))
                        for i in range(1200))
        session.add_all(PlayersAction(player_id_id=player.id, action_type="PUNISH", reason="Large payload "*100,
                                     by="Synthetic", time=LOCAL_NOW) for _ in range(1200))
        player_id = player.id
    with maker() as session:
        baseline = session.get(PlayerID, player_id)
        expected_total = baseline.get_total_playtime_seconds()
        assert expected_total == 1200, {
            "baseline_total": expected_total,
            "sample": [(s.start, s.end, s.start_event_us, s.end_event_us) for s in baseline.sessions[:3]],
        }
    monkeypatch.setattr(PlayerID, "to_dict", Mock(side_effect=AssertionError("full profile serializer used")))
    statements = []
    def record(_conn, _cursor, sql, _params, context, _many):
        statements.append((sql.lower(), context.execution_options))
    def reject_history_model(_instance, _context):
        raise AssertionError("history ORM instance loaded")
    event.listen(engine, "before_cursor_execute", record)
    event.listen(PlayerSession, "load", reject_history_model)
    event.listen(PlayersAction, "load", reject_history_model)
    try:
        profile = get_projection(compact=True)["players"][0]
    finally:
        event.remove(engine, "before_cursor_execute", record)
        event.remove(PlayerSession, "load", reject_history_model)
        event.remove(PlayersAction, "load", reject_history_model)
    assert profile["sessions_count"] == 1200
    assert profile["total_playtime_seconds"] == expected_total
    assert profile["penalty_count"]["PUNISH"] == 1200
    actions = [sql for sql,_ in statements if "players_actions" in sql]
    assert len(actions) == 1 and "count(" in actions[0] and "group by" in actions[0]
    assert "players_actions.reason" not in actions[0]
    assert any(options.get("yield_per") == 512 for _sql,options in statements)


def test_records_api_keeps_legacy_default_and_forwards_compact(monkeypatch):
    from rcon import api_commands, player_presence
    search = Mock(return_value={"players":[],"total":0})
    monkeypatch.setattr(api_commands, "get_players_by_appearance", search)
    monkeypatch.setattr(player_presence, "read_other_servers", lambda *_: ({},set()))
    source = SimpleNamespace(get_player_ids=lambda: [], without_retries=nullcontext)
    api_commands.RconAPI.get_players_history(source)
    assert search.call_args.kwargs["compact"] is False
    api_commands.RconAPI.get_players_history(source, compact="true")
    assert search.call_args.kwargs["compact"] == "true"


def test_summary_query_count_is_independent_of_page_population(record_database):
    engine, maker = record_database
    with maker.begin() as session:
        for index in range(50):
            make_player(session, f"synthetic-{index:03}")
    counts = []
    for size in (1, 50):
        queries = []
        def record(_conn, _cursor, sql, *_args):
            queries.append(sql)
        event.listen(engine, "before_cursor_execute", record)
        try:
            result = get_projection(compact=True, page_size=size)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        assert len(result["players"]) == size
        counts.append(len(queries))
    assert counts[1] == counts[0]
