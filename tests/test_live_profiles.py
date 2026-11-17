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
    assert profile["current_session_start"] is None

    local_start = datetime(2026, 8, 26, 10, tzinfo=timezone.utc)
    player.sessions = [
        PlayerSession(id=2, server_number=4, start=datetime(2026, 8, 26, 11),
                      created=datetime(2026, 8, 26, 11)),
        PlayerSession(id=1, server_number=3, start=local_start.replace(tzinfo=None),
                      start_event_us=int(local_start.timestamp() * 1_000_000),
                      created=datetime(2026, 8, 26, 10)),
    ]
    profile = player.to_dict(limit_sessions=1, preloaded_vips=[preloaded_vip])
    assert profile["sessions"][0]["id"] == 2
    assert profile["current_session_start"] == local_start
    player.sessions[1].end_event_us = int(local_start.timestamp() * 1_000_000) + 1
    assert player.to_dict(limit_sessions=1, preloaded_vips=[preloaded_vip])["current_session_start"] is None


def test_empty_live_profile_request_does_not_open_a_database_session(monkeypatch):
    def fail_if_called():
        raise AssertionError("empty live profile requests must not touch the database")

    monkeypatch.setattr("rcon.player_history.enter_session", fail_if_called)

    assert get_live_profiles([]) == []


def test_total_playtime_counts_active_local_session_when_newer_remote_session_ended(monkeypatch):
    from datetime import timedelta
    from rcon.models import PlayerID, PlayerSession
    monkeypatch.setattr('rcon.models.get_server_number', lambda: '3')
    now = datetime.now(timezone.utc)
    local_start = now - timedelta(hours=1)
    remote_start = now - timedelta(minutes=5)
    remote_end = now - timedelta(minutes=3)
    player = PlayerID(player_id='synthetic-player')
    player.sessions = [
        PlayerSession(id=1, server_number=3, start=local_start.replace(tzinfo=None),
                      start_event_us=int(local_start.timestamp() * 1_000_000)),
        PlayerSession(id=2, server_number=4, start=remote_start.replace(tzinfo=None),
                      end=remote_end.replace(tzinfo=None),
                      start_event_us=int(remote_start.timestamp() * 1_000_000),
                      end_event_us=int(remote_end.timestamp() * 1_000_000)),
    ]
    # One hour of active local play plus two minutes of completed remote play.
    assert 3720 <= player.get_total_playtime_seconds() < 3730


def test_total_playtime_keeps_newest_active_remote_session_fallback(monkeypatch):
    from datetime import timedelta
    from rcon.models import PlayerID, PlayerSession
    monkeypatch.setattr('rcon.models.get_server_number', lambda: '3')
    now = datetime.now(timezone.utc)
    local = now - timedelta(hours=1)
    remote = now - timedelta(minutes=5)
    player = PlayerID(player_id='synthetic-player')
    player.sessions = [
        PlayerSession(id=1, server_number=3, start=local.replace(tzinfo=None),
                      start_event_us=int(local.timestamp() * 1_000_000)),
        PlayerSession(id=2, server_number=4, start=remote.replace(tzinfo=None),
                      start_event_us=int(remote.timestamp() * 1_000_000)),
    ]
    assert 300 <= player.get_total_playtime_seconds() < 310


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


def test_absolute_disconnect_closes_live_profile_even_without_legacy_end(live_profile_database):
    _engine, sessions = live_profile_database
    now = datetime.now(timezone.utc)
    with sessions.begin() as session:
        player = PlayerID(player_id='synthetic-ended-absolute', steam_id=None, created=now.replace(tzinfo=None))
        session.add(player)
        session.flush()
        session.add(PlayerSession(player_id_id=player.id, server_number=1,
            start=(now - timedelta(minutes=10)).replace(tzinfo=None), end=None,
            start_event_us=int((now - timedelta(minutes=10)).timestamp() * 1_000_000),
            end_event_us=int((now - timedelta(minutes=1)).timestamp() * 1_000_000)))
    assert get_live_profiles(['synthetic-ended-absolute'])[0]['current_playtime_seconds'] == 0


def test_live_profile_current_session_is_local_but_count_remains_global(live_profile_database, monkeypatch):
    _engine, sessions = live_profile_database
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with sessions.begin() as session:
        player = PlayerID(player_id="synthetic-multiserver", steam_id=None, created=now)
        session.add(player)
        session.flush()
        session.add_all([
            PlayerSession(player_id_id=player.id, start=now-timedelta(minutes=30), end=None,
                          created=now-timedelta(minutes=30), server_number=1, server_name="one"),
            PlayerSession(player_id_id=player.id, start=now-timedelta(minutes=10), end=now-timedelta(minutes=1),
                          created=now-timedelta(minutes=10), server_number=2, server_name="two"),
        ])
    local = get_live_profiles(["synthetic-multiserver"])[0]
    assert local["sessions_count"] == 2
    assert 1795 <= local["current_playtime_seconds"] <= 1810
    monkeypatch.setenv("SERVER_NUMBER", "2")
    other = get_live_profiles(["synthetic-multiserver"])[0]
    assert other["sessions_count"] == 2 and other["current_playtime_seconds"] == 0
    monkeypatch.setenv("SERVER_NUMBER", "3")
    missing = get_live_profiles(["synthetic-multiserver"])[0]
    assert missing["sessions_count"] == 2 and missing["current_playtime_seconds"] == 0


def test_late_older_connect_does_not_replace_newer_live_session(live_profile_database):
    _engine, sessions = live_profile_database
    now = datetime.now(timezone.utc)
    with sessions.begin() as session:
        player = PlayerID(player_id='synthetic-late-connect', steam_id=None, created=now.replace(tzinfo=None))
        session.add(player)
        session.flush()
        old = now - timedelta(hours=1)
        recent = now - timedelta(minutes=5)
        session.add_all([
            PlayerSession(player_id_id=player.id, start=recent.replace(tzinfo=None), end=None,
                          start_event_us=int(recent.timestamp() * 1_000_000),
                          created=(now - timedelta(minutes=4)).replace(tzinfo=None), server_number=1),
            PlayerSession(player_id_id=player.id, start=old.replace(tzinfo=None),
                          end=(old + timedelta(minutes=10)).replace(tzinfo=None),
                          start_event_us=int(old.timestamp() * 1_000_000),
                          created=now.replace(tzinfo=None), server_number=1),
        ])
    profile = get_live_profiles(['synthetic-late-connect'])[0]
    assert profile['sessions_count'] == 2
    assert 295 <= profile['current_playtime_seconds'] <= 310


def test_newer_legacy_session_retains_creation_time_fallback(live_profile_database):
    _engine, sessions = live_profile_database
    now = datetime.now(timezone.utc)
    with sessions.begin() as session:
        player = PlayerID(player_id='synthetic-mixed-sessions', steam_id=None, created=now.replace(tzinfo=None))
        session.add(player)
        session.flush()
        old = now - timedelta(hours=1)
        legacy = now - timedelta(minutes=5)
        session.add_all([
            PlayerSession(player_id_id=player.id, start=legacy.replace(tzinfo=None), end=None,
                          start_event_us=None, created=legacy.replace(tzinfo=None), server_number=1),
            PlayerSession(player_id_id=player.id, start=old.replace(tzinfo=None),
                          end=(old + timedelta(minutes=10)).replace(tzinfo=None),
                          start_event_us=int(old.timestamp() * 1_000_000),
                          created=now.replace(tzinfo=None), server_number=1),
        ])
    profile = get_live_profiles(['synthetic-mixed-sessions'])[0]
    assert profile['sessions_count'] == 2
    assert 295 <= profile['current_playtime_seconds'] <= 310


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
