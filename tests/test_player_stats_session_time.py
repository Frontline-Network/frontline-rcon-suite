"""Round playtime accounting with synthetic logs and no external services."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import os

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon import player_stats
from rcon.types import AllLogTypes


@pytest.fixture
def compute(monkeypatch):
    monkeypatch.setattr(player_stats, "enter_session", lambda: nullcontext(None))
    monkeypatch.setattr(player_stats, "get_player_profile_by_player_ids", lambda *_: [])
    stats = player_stats.TimeWindowStats.__new__(player_stats.TimeWindowStats)
    start = datetime(2026, 10, 24, tzinfo=timezone.utc)

    def run(events, duration=3600, cooldown=100, warmup=None):
        logs = [
            {
                "action": action,
                "event_time": start + timedelta(seconds=second),
                "player_name_1": "Player",
                "player_id_1": "player",
            }
            for second, action in events
        ]
        # Exercise the real session builder; combat scoring is tested elsewhere.
        monkeypatch.setattr(stats, "get_stats_by_player", lambda **_: None)
        stats._get_players_stats_from_logs(
            logs,
            start,
            start + timedelta(seconds=duration),
            offset_cooldown_time_seconds=cooldown,
            **({} if warmup is None else {"offset_warmup_time_seconds": warmup}),
        )
        return stats.times["player"]["total"]

    return run


CONNECTED = AllLogTypes.connected
DISCONNECTED = AllLogTypes.disconnected
ACTIVITY = AllLogTypes.kill


@pytest.mark.parametrize("warmup,expected", [(0, 3600), (120, 3480), (300, 3300)])
def test_inferred_start_uses_requested_warmup(compute, warmup, expected):
    assert compute([(20, ACTIVITY)], cooldown=0, warmup=warmup) == expected


def test_inferred_start_uses_public_default_warmup(compute):
    assert compute([(20, ACTIVITY)], cooldown=0) == 3480


def test_warmup_does_not_shift_observed_connect(compute):
    assert compute([(200, CONNECTED)], cooldown=0, warmup=300) == 3400


def test_custom_warmup_cannot_make_short_round_negative(compute):
    assert compute([(20, ACTIVITY)], duration=60, cooldown=0, warmup=300) == 0


def test_historical_name_is_latest_even_when_logs_are_out_of_order(monkeypatch):
    monkeypatch.setattr(player_stats, "enter_session", lambda: nullcontext(None))
    monkeypatch.setattr(player_stats, "get_player_profile_by_player_ids", lambda *_: [])
    stats = player_stats.TimeWindowStats.__new__(player_stats.TimeWindowStats)
    monkeypatch.setattr(stats, "get_stats_by_player", lambda **kwargs: kwargs["players"])
    start = datetime(2026, 10, 24, tzinfo=timezone.utc)
    logs = [
        {"action": ACTIVITY, "event_time": start + timedelta(seconds=second),
         "player_name_1": name, "player_id_1": "player"}
        for second, name in [(300, "Latest"), (100, "Earlier")]
    ]

    assert stats._get_players_stats_from_logs(logs, start, start + timedelta(hours=1)) == [
        {"name": "Latest", "player_id": "player"}
    ]


@pytest.mark.parametrize("remaining", [0, 1, 51, 99, 100, 101])
def test_late_join_cannot_create_negative_playtime(compute, remaining):
    assert compute([(3600 - remaining, CONNECTED)]) == max(0, remaining - 100)


def test_short_session_before_warmup_is_zero(compute):
    assert compute([(20, ACTIVITY), (30, DISCONNECTED)]) == 0


def test_negative_last_session_does_not_subtract_previous_playtime(compute):
    assert compute([(200, CONNECTED), (800, DISCONNECTED), (3549, CONNECTED)]) == 600


def test_negative_first_session_does_not_subtract_reconnect(compute):
    assert compute([(20, ACTIVITY), (30, DISCONNECTED), (300, CONNECTED)]) == 3200


def test_normal_multiple_sessions_are_unchanged(compute):
    assert compute([(200, CONNECTED), (800, DISCONNECTED), (1000, CONNECTED)]) == 3100


def test_live_stats_have_no_cooldown_discount(compute):
    assert compute([(3549, CONNECTED)], cooldown=0) == 51


def test_short_round_with_inferred_start_is_zero(compute):
    assert compute([(20, ACTIVITY)], duration=60) == 0


def test_session_is_bounded_by_requested_window(compute):
    assert compute([(-20, CONNECTED), (4000, DISCONNECTED)]) == 3600


@pytest.mark.parametrize(
    "events",
    [
        [(3506, ACTIVITY), (3506, CONNECTED)],
        [(3506, CONNECTED), (3506, ACTIVITY)],
    ],
)
def test_same_second_activity_does_not_infer_an_extra_session(compute, events):
    assert compute(events, cooldown=0) == 94
    assert compute(events, cooldown=100) == 0


def test_duplicate_disconnect_and_reconnect_reconstruct_207_seconds(compute):
    events = [
        (15, CONNECTED),
        (212, DISCONNECTED),
        (212, DISCONNECTED),
        (339, CONNECTED),
        (349, DISCONNECTED),
    ]
    assert compute(events) == 207
    assert compute(list(reversed(events))) == 207


def test_duplicate_connect_is_counted_once(compute):
    assert compute([(200, CONNECTED), (200, CONNECTED), (800, DISCONNECTED)]) == 600
