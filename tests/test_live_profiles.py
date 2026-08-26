from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from rcon.models import PlayerAccount, PlayerID, PlayerSoldier, PlayerVIP, WatchList
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
