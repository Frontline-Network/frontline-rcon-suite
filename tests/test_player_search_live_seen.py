"""Last-seen filters use confirmed current players, never stale open sessions."""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
import os
import time
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, Session
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon import api_commands, player_history
from rcon.models import PlayerAccount, PlayerID, PlayerName, PlayerSession, PlayerVIP, SteamInfo


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    monkeypatch.setattr(PlayerSession.__table__.c.end, "nullable", True)
    for model in (PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo):
        model.__table__.create(engine)
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
    monkeypatch.setattr(player_history, "enter_session", session)
    monkeypatch.setattr(Query, "options", lambda self, *args, **kwargs: self)
    monkeypatch.setattr(PlayerID, "to_dict", lambda self, **kwargs: {"player_id": self.player_id})
    monkeypatch.setattr(player_history, "get_player_identity_links", lambda sess, players: {p.player_id: {} for p in players})
    now = datetime(2026, 11, 16, 12)
    with Session(engine) as sess:
        for pid, server in [("console-online", 3), ("stale-open", 3), ("other-server-open", 4)]:
            player = PlayerID(player_id=pid, created=now - timedelta(hours=4))
            sess.add(player)
            sess.flush()
            sess.add(PlayerSession(player_id_id=player.id, start=now - timedelta(hours=3),
                                   created=now - timedelta(hours=3), end=None,
                                   server_number=server, server_name="synthetic"))
        sess.commit()
    yield engine
    engine.dispose()


def test_only_verified_online_player_matches_recent_filter(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    result = player_history.get_players_by_appearance(
        last_seen_from=now - timedelta(hours=1), online_now_ids={"console-online"}, observed_at=now)
    assert result["total"] == 1
    assert result["local_online_snapshot_available"] is True
    assert result["players"][0]["player_id"] == "console-online"
    assert result["players"][0]["last_seen_timestamp_ms"] == int(now.timestamp() * 1000)


def test_old_filter_and_pagination_use_the_same_verified_timestamp(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    old = player_history.get_players_by_appearance(
        last_seen_till=now - timedelta(hours=1), online_now_ids={"console-online"}, observed_at=now)
    assert {p["player_id"] for p in old["players"]} == {"stale-open", "other-server-open"}
    first = player_history.get_players_by_appearance(page_size=1, online_now_ids={"console-online"}, observed_at=now)
    assert first["players"][0]["player_id"] == "console-online"


def test_unavailable_snapshot_does_not_invent_online_presence(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    result = player_history.get_players_by_appearance(last_seen_from=now - timedelta(hours=1),
                                                       online_now_ids=None, observed_at=now)
    assert result["total"] == 0
    assert result["local_online_snapshot_available"] is False


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="requires controllable local timezone")
def test_offset_filters_keep_legacy_history_semantics_in_non_utc_process(database, monkeypatch):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    try:
        with monkeypatch.context() as scope:
            scope.setenv("TZ", "Europe/Berlin")
            time.tzset()
            threshold = datetime(2026, 11, 16, 12, 30, tzinfo=timezone(timedelta(hours=1)))
            recent = player_history.get_players_by_appearance(last_seen_from=threshold,
                online_now_ids={"console-online"}, observed_at=now)
            assert [p["player_id"] for p in recent["players"]] == ["console-online"]
            old = player_history.get_players_by_appearance(last_seen_till=threshold,
                online_now_ids={"console-online"}, observed_at=now)
            assert {p["player_id"] for p in old["players"]} == {"stale-open", "other-server-open"}
    finally:
        time.tzset()


def test_api_passes_full_console_ids_and_handles_snapshot_failure(monkeypatch):
    search = Mock(return_value={"total": 0, "players": []})
    monkeypatch.setattr(api_commands, "get_players_by_appearance", search)
    api = SimpleNamespace(get_player_ids=Mock(return_value=[("Same", "console-1"), ("Same", "console-2")]),
                          without_retries=nullcontext)
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] == {"console-1", "console-2"}
    api.get_player_ids.side_effect = OSError("synthetic outage")
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None
    api.get_player_ids.side_effect = None
    api.get_player_ids.return_value = [("Valid", "console-1"), ("Invalid", None)]
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None
    api.get_player_ids.return_value = [("One", "console-1"), ("Two", "console-1")]
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None


@pytest.mark.skipif(not os.environ.get("RCON_SEARCH_TEST_DATABASE"), reason="requires isolated PostgreSQL")
def test_postgres_filters_order_and_console_ids_with_utc_offsets(monkeypatch):
    base = create_engine(os.environ["RCON_SEARCH_TEST_DATABASE"])
    schema = "player_seen_" + uuid.uuid4().hex
    with base.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema})
    monkeypatch.setattr(PlayerSession.__table__.c.end, "nullable", True)
    try:
        for model in (PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo):
            model.__table__.create(engine)
        @contextmanager
        def session():
            with Session(engine) as sess:
                yield sess
        monkeypatch.setattr(player_history, "enter_session", session)
        monkeypatch.setattr(Query, "options", lambda self, *args, **kwargs: self)
        monkeypatch.setattr(PlayerID, "to_dict", lambda self, **kwargs: {"player_id": self.player_id})
        monkeypatch.setattr(player_history, "get_player_identity_links", lambda sess, players: {p.player_id: {} for p in players})
        now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
        with Session(engine) as sess:
            for pid, server in [("console-online", 3), ("orphan-other-server", 4)]:
                player = PlayerID(player_id=pid, created=datetime(2026, 11, 16, 8))
                sess.add(player)
                sess.flush()
                sess.add(PlayerSession(player_id_id=player.id, start=datetime(2026, 11, 16, 9),
                                       created=datetime(2026, 11, 16, 9), end=None,
                                       server_number=server, server_name="synthetic"))
            sess.commit()
        threshold = datetime(2026, 11, 16, 12, 30, tzinfo=timezone(timedelta(hours=1)))
        result = player_history.get_players_by_appearance(last_seen_from=threshold,
            online_now_ids={"console-online"}, observed_at=now, page_size=1)
        assert result["total"] == 1 and result["players"][0]["player_id"] == "console-online"
        assert result["players"][0]["last_seen_timestamp_ms"] == int(now.timestamp() * 1000)
    finally:
        with base.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        base.dispose()
