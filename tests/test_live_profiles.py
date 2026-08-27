from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from rcon.models import (
    Blacklist,
    BlacklistRecord,
    PlayerAccount,
    PlayerFlag,
    PlayerID,
    PlayersAction,
    PlayerSession,
    PlayerSoldier,
    PlayerVIP,
    WatchList,
)
from rcon.player_history import (
    _current_playtime_seconds,
    _watchlist_dict,
    get_live_profiles,
)


def test_current_playtime_uses_only_active_latest_session():
    started_at = datetime.now() - timedelta(minutes=15)

    active = SimpleNamespace(start=started_at, created=started_at, end=None)
    ended = SimpleNamespace(
        start=started_at,
        created=started_at,
        end=datetime.now(),
    )

    assert 14 * 60 <= _current_playtime_seconds(active) <= 16 * 60
    assert _current_playtime_seconds(ended) == 0
    assert _current_playtime_seconds(None) == 0


def test_watchlist_projection_does_not_lazy_load_player_relationship():
    player = PlayerID(id=17, player_id="live-player")
    player.watchlist = WatchList(
        id=4,
        modified=datetime(2026, 8, 26, 12, 0),
        is_watched=True,
        reason="Observe",
        by="Admin",
        count=2,
    )

    assert _watchlist_dict(player) == {
        "id": 4,
        "modified": datetime(2026, 8, 26, 12, 0),
        "player_id": "live-player",
        "is_watched": True,
        "reason": "Observe",
        "by": "Admin",
        "count": 2,
    }


def test_bulk_profile_serialization_accepts_preloaded_vips(monkeypatch):
    monkeypatch.setenv("SERVER_NUMBER", "3")
    player = PlayerID(
        id=21,
        player_id="bulk-player",
        steam_id=None,
        created=datetime(2026, 8, 1, 10, 0),
    )
    player.names = []
    player.sessions = []
    player.received_actions = []
    player.blacklists = []
    player.flags = []
    player.watchlist = None
    player.steaminfo = None
    player.soldier = PlayerSoldier(
        eos_id=None,
        name="Bulk Player",
        level=42,
        platform="steam",
        clan_tag=None,
        updated=datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
    )
    player.account = PlayerAccount(
        name=None,
        discord_id=None,
        is_member=False,
        country=None,
        lang="en",
        updated=datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
    )
    preloaded_vip = PlayerVIP(
        server_number=3,
        expiration=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    profile = player.to_dict(limit_sessions=1, preloaded_vips=[preloaded_vip])

    assert profile["vips"] == [
        {
            "server_number": 3,
            "expiration": datetime(2026, 9, 1, tzinfo=timezone.utc),
        }
    ]
    assert profile["is_vip"] is True
    assert profile["sessions_count"] == 0


def test_empty_live_profile_request_does_not_open_a_database_session(monkeypatch):
    def fail_if_called():
        raise AssertionError("empty live profile requests must not touch the database")

    monkeypatch.setattr("rcon.player_history.enter_session", fail_if_called)

    assert get_live_profiles([]) == []


@pytest.fixture
def live_profile_database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (
        PlayerID,
        PlayerFlag,
        WatchList,
        PlayerSoldier,
        PlayerSession,
        PlayersAction,
        Blacklist,
        BlacklistRecord,
    ):
        model.__table__.create(engine)

    sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def enter_test_session():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr("rcon.player_history.enter_session", enter_test_session)
    monkeypatch.setenv("SERVER_NUMBER", "1")
    yield engine, sessions
    engine.dispose()


def test_live_profile_query_count_is_constant_and_joins_scalar_relationships(
    live_profile_database,
):
    engine, sessions = live_profile_database
    now = datetime.now(timezone.utc)
    player_ids = [f"live-player-{index:03d}" for index in range(50)]

    with sessions.begin() as session:
        for index, player_id in enumerate(player_ids):
            player = PlayerID(
                player_id=player_id,
                steam_id=None,
                created=now.replace(tzinfo=None),
            )
            player.flags = [PlayerFlag(flag="seeded", comment=None, modified=now)]
            player.watchlist = WatchList(
                modified=now,
                is_watched=index == 0,
                reason="Observe" if index == 0 else "",
                by="Test",
                count=1 if index == 0 else 0,
            )
            player.soldier = PlayerSoldier(
                eos_id=None,
                name=f"Player {index}",
                level=index,
                platform="steam",
                clan_tag=None,
                updated=now,
            )
            session.add(player)

    def load_with_query_count(requested_player_ids):
        query_count = 0

        def count_query(*_args):
            nonlocal query_count
            query_count += 1

        event.listen(engine, "before_cursor_execute", count_query)
        try:
            profiles = get_live_profiles(requested_player_ids)
        finally:
            event.remove(engine, "before_cursor_execute", count_query)
        return profiles, query_count

    one_profile, one_player_queries = load_with_query_count(player_ids[:1])
    all_profiles, full_roster_queries = load_with_query_count(player_ids)

    assert one_player_queries == 5
    assert full_roster_queries == one_player_queries
    assert len(all_profiles) == 50
    assert one_profile[0]["flags"][0]["flag"] == "seeded"
    assert one_profile[0]["watchlist"]["reason"] == "Observe"
    assert one_profile[0]["soldier"] == {
        "level": 0,
        "platform": "steam",
        "clan_tag": None,
    }
