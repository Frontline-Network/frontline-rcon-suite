"""Round boundaries must survive map-loading RCON outages (HLL and HLLV)."""

import os
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import fakeredis
import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon import hooks, utils
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.logs.loop import LogLoop
from rcon.maps import GameMode
from rcon.utils import MapsHistory, layer_matches_match_log


def event(title, timestamp, *, end=False):
    raw = (
        f"MATCH ENDED `{title}` ALLIED (3 - 2) AXIS" if end else f"MATCH START {title}"
    )
    return {
        "raw": raw,
        "timestamp_ms": timestamp * 1000,
        "event_time": datetime.fromtimestamp(timestamp, UTC),
    }


@pytest.fixture
def state(monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setattr(utils, "get_redis_pool", lambda: client.connection_pool)
    monkeypatch.setattr(hooks, "get_redis_client", lambda: client)
    monkeypatch.setattr(hooks, "invalidates", lambda *args: nullcontext())
    history = MapsHistory()
    vote = Mock(enabled=False)
    monkeypatch.setattr(hooks, "VoteMap", lambda: vote)
    backfill, stats = Mock(), Mock()
    monkeypatch.setattr(hooks, "save_missing_match_logs_worker", backfill)
    monkeypatch.setattr(hooks, "record_stats_worker", stats)
    return history, vote, backfill, stats


def rcon_for(profile=HLL_PROFILE):
    rcon = Mock(game_profile=profile)
    rcon.get_gamestate.side_effect = TimeoutError("map loading")
    return rcon


@pytest.mark.parametrize(
    "profile,title,expected",
    [
        (HLL_PROFILE, "UTAH BEACH Warfare", "utahbeach_warfare"),
        (HLL_PROFILE, "CARENTAN Conquest", "car_l_1944_conquest_day"),
        (HLLV_PROFILE, "VẠN TƯỜNG US Offensive", "wdeva_offensiveus_day"),
        (HLLV_PROFILE, "CAM RANH PORT Warfare", "wdeve_warfare_day"),
    ],
)
def test_start_is_persisted_without_live_query(state, profile, title, expected):
    history, _, backfill, stats = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    rcon = rcon_for(profile)

    hooks.handle_new_match_start(rcon, event(title, 2_000))

    assert history[0]["name"].lower() == expected.lower()
    assert history[0]["start"] == 2_000
    assert history[0]["end"] is None
    assert history[0]["guessed"] is True
    assert history[0]["match_time"] == 0
    assert history[1]["end"] == 2_000
    rcon.get_gamestate.assert_not_called()
    backfill.assert_called_once_with(history[1])
    stats.assert_called_once_with(history[1], backfill.return_value)


def test_first_start_has_no_previous_round(state):
    history, _, backfill, stats = state
    hooks.handle_new_match_start(rcon_for(), event("CARENTAN Warfare", 2_000))
    assert len(history) == 1
    backfill.assert_not_called()
    stats.assert_not_called()


@pytest.mark.parametrize("timestamp", [1_999, 2_000])
def test_duplicate_or_older_start_does_not_reset_round(state, timestamp):
    history, _, backfill, stats = state
    history.save_new_map("carentan_warfare", start_timestamp=2_000)
    original = history[0]
    original["player_stats"] = {"player": {"combat": 100}}
    history.update(0, original)
    history.red.set("GAME_LAYOUT", '{"requested":["next"]}')

    hooks.handle_new_match_start(rcon_for(), event("UTAH BEACH Warfare", timestamp))

    assert list(history) == [original]
    assert history.red.get("GAME_LAYOUT") is not None
    stats.assert_not_called()
    backfill.assert_not_called()


def test_old_event_uses_logged_map_not_current_live_map(state):
    history, *_ = state
    rcon = rcon_for()
    hooks.handle_new_match_start(rcon, event("UTAH BEACH Warfare", 1_000))
    assert history[0]["name"] == "utahbeach_warfare"
    rcon.get_gamestate.assert_not_called()


@pytest.mark.parametrize("failure", ["vote", "backfill"])
def test_auxiliary_failures_cannot_block_stats(state, failure):
    history, vote, backfill, stats = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    if failure == "vote":
        vote.enabled = True
        vote.record_result.side_effect = RuntimeError("Discord unavailable")
    else:
        backfill.side_effect = RuntimeError("failed backfill enqueue")

    hooks.handle_new_match_start(rcon_for(), event("UTAH BEACH Warfare", 2_000))

    assert len(history) == 2
    stats.assert_called_once_with(
        history[1], None if failure == "backfill" else backfill.return_value
    )


@pytest.mark.parametrize(
    "profile,map_id,title",
    [
        (HLL_PROFILE, "utahbeach_warfare_night", "UTAH BEACH Warfare"),
        (HLL_PROFILE, "car_l_1944_conquest_day", "CARENTAN Conquest"),
        (HLLV_PROFILE, "wdeva_offensivenva_day", "VẠN TƯỜNG NVA Offensive"),
    ],
)
def test_end_uses_cached_round_not_live_map(state, profile, map_id, title):
    history, *_ = state
    history.save_new_map(map_id, start_timestamp=1_000, guessed=False)
    rcon = rcon_for(profile)
    hooks.record_map_end(rcon, event(title, 2_000, end=True))
    assert history[0]["end"] == 2_000
    rcon.get_gamestate.assert_not_called()


@pytest.mark.parametrize(
    "title,timestamp",
    [
        ("UTAH BEACH Warfare", 2_000),
        ("CARENTAN Conquest", 2_000),
        ("CARENTAN NIGHT Warfare", 2_000),
        ("CARENTAN Warfare", 999),
        ("CARENTAN Warfare", 1_000),
        ("UNKNOWN Warfare", 2_000),
    ],
)
def test_unrelated_or_stale_end_does_not_change_round(state, title, timestamp):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000, guessed=False)
    original = history[0]
    hooks.record_map_end(rcon_for(), event(title, timestamp, end=True))
    assert history[0] == original


def test_duplicate_end_never_extends_closed_round(state):
    history, *_ = state
    rcon = rcon_for()
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    hooks.record_map_end(rcon, event("CARENTAN Warfare", 2_000, end=True))
    hooks.record_map_end(rcon, event("CARENTAN Warfare", 3_000, end=True))
    assert history[0]["end"] == 2_000


def test_end_without_start_does_not_create_phantom_round(state):
    history, *_ = state
    hooks.record_map_end(rcon_for(), event("CARENTAN Warfare", 2_000, end=True))
    assert len(history) == 0


def test_end_can_refine_unspecified_weather_without_any_live_poll(state):
    history, *_ = state
    rcon = rcon_for()
    hooks.handle_new_match_start(rcon, event("CARENTAN Warfare", 1_000))
    hooks.record_map_end(rcon, event("CARENTAN NIGHT Warfare", 2_000, end=True))
    assert history[0]["name"] == "carentan_warfare_night"
    assert history[0]["end"] == 2_000


@pytest.mark.parametrize(
    "previous,missing,next_map",
    [
        ("JUNO BEACH Warfare", "STALINGRAD Warfare", "TOBRUK Warfare"),
        ("TOBRUK Warfare", "CARENTAN Warfare", "UTAH BEACH Warfare"),
        (
            "ST MARIE DU MONT Warfare",
            "UTAH BEACH Warfare",
            "SAINTE-MÈRE-ÉGLISE Warfare",
        ),
    ],
)
def test_observed_hll1_rounds_stay_separate_during_outage(
    state, previous, missing, next_map
):
    history, _, _, stats = state
    rcon = rcon_for()
    hooks.handle_new_match_start(rcon, event(previous, 1_000))
    hooks.record_map_end(rcon, event(previous, 6_400, end=True))
    hooks.handle_new_match_start(rcon, event(missing, 6_510))
    hooks.record_map_end(rcon, event(missing, 13_710, end=True))
    hooks.handle_new_match_start(rcon, event(next_map, 13_820))

    assert [(m["start"], m["end"]) for m in history] == [
        (13_820, None),
        (6_510, 13_710),
        (1_000, 6_400),
    ]
    assert stats.call_count == 2
    assert stats.call_args_list[0].args[0]["end"] == 6_400
    assert stats.call_args_list[1].args[0]["start"] == 6_510


def test_consecutive_rounds_on_same_layer_are_not_duplicates(state):
    history, _, _, stats = state
    rcon = rcon_for()
    hooks.handle_new_match_start(rcon, event("CARENTAN Warfare", 1_000))
    hooks.handle_new_match_start(rcon, event("CARENTAN Warfare", 2_000))
    hooks.record_map_end(rcon, event("CARENTAN Warfare", 1_900, end=True))
    assert [(m["start"], m["end"]) for m in history] == [(2_000, None), (1_000, 2_000)]
    stats.assert_called_once()


def test_cache_end_requires_expected_identity(state):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    original = history[0]
    assert history.save_map_end("utahbeach_warfare", 2_000) is None
    assert history.save_map_end("carentan_warfare", 2_000, start_timestamp=500) is None
    assert history[0] == original


def test_cache_start_rejects_old_duplicate_and_inside_closed_round(state):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    history.save_map_end("carentan_warfare", 2_000)
    original = list(history)
    for ts in (999, 1_000, 1_500):
        assert history.save_new_map("utahbeach_warfare", start_timestamp=ts) is None
    assert list(history) == original


@pytest.mark.parametrize("operation", ["start", "end"])
def test_cache_transition_retries_without_losing_concurrent_stats(
    state, monkeypatch, operation
):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    real_pipeline = history.red.pipeline
    changed = False

    def pipeline(*args, **kwargs):
        pipe = real_pipeline(*args, **kwargs)
        execute = pipe.execute

        def execute_with_competing_write(*args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                current = history[0]
                current["player_stats"] = {"player": {"combat": 123}}
                history.update(0, current)
            return execute(*args, **kwargs)

        pipe.execute = execute_with_competing_write
        return pipe

    monkeypatch.setattr(history.red, "pipeline", pipeline)
    if operation == "start":
        history.save_new_map("utahbeach_warfare", start_timestamp=2_000)
        previous = history[1]
        assert len(history) == 2
    else:
        history.save_map_end("carentan_warfare", 2_000, start_timestamp=1_000)
        previous = history[0]
        assert len(history) == 1
    assert previous["end"] == 2_000
    assert previous["player_stats"] == {"player": {"combat": 123}}


@pytest.mark.parametrize("operation", ["start", "end"])
def test_failed_cache_transaction_keeps_original_round_intact(
    state, monkeypatch, operation
):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    original = list(history)
    real_pipeline = history.red.pipeline

    def pipeline(*args, **kwargs):
        pipe = real_pipeline(*args, **kwargs)
        pipe.execute = Mock(side_effect=ConnectionError("Redis unavailable"))
        return pipe

    monkeypatch.setattr(history.red, "pipeline", pipeline)
    with pytest.raises(ConnectionError):
        if operation == "start":
            history.save_new_map("utahbeach_warfare", start_timestamp=2_000)
        else:
            history.save_map_end("carentan_warfare", 2_000)
    assert list(history) == original


def test_finished_worker_cannot_overwrite_round_when_new_start_shifts_index(
    state, monkeypatch
):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    saved = history[0]
    saved["player_stats"] = {"player": {"combat": 100}}
    history.update(0, saved)
    history.save_new_map("utahbeach_warfare", start_timestamp=2_000)
    saved = history[1]
    real_pipeline = history.red.pipeline
    shifted = False

    def pipeline(*args, **kwargs):
        pipe = real_pipeline(*args, **kwargs)
        execute = pipe.execute

        def execute_after_next_start(*args, **kwargs):
            nonlocal shifted
            if not shifted:
                shifted = True
                history.save_new_map("tobruk_warfare_day", start_timestamp=3_000)
            return execute(*args, **kwargs)

        pipe.execute = execute_after_next_start
        return pipe

    monkeypatch.setattr(history.red, "pipeline", pipeline)
    history.clear_recorded_stats(saved)

    assert [m["start"] for m in history] == [3_000, 2_000, 1_000]
    assert history[1]["name"] == "utahbeach_warfare"
    assert history[2]["player_stats"] == {}


def test_cache_cleanup_preserves_active_and_nonmatching_rounds(state):
    history, *_ = state
    history.save_new_map("carentan_warfare", start_timestamp=1_000)
    current = history[0]
    current["player_stats"] = {"player": {"combat": 100}}
    history.update(0, current)
    history.clear_recorded_stats(current)
    assert history[0] == current
    history.save_new_map("utahbeach_warfare", start_timestamp=2_000)
    original = list(history)
    history.clear_recorded_stats({**history[1], "start": 999})
    assert list(history) == original


@pytest.mark.parametrize(
    "profile,title,map_id",
    [
        (HLL_PROFILE, "CARENTAN Warfare", "carentan_warfare_night"),
        (HLL_PROFILE, "CARENTAN Conquest", "car_l_1944_conquest_day"),
        (HLLV_PROFILE, "VẠN TƯỜNG Offensive", "wdeva_offensivenva_day"),
    ],
)
def test_polling_recovers_precise_layer_after_outage(state, profile, title, map_id):
    history, *_ = state
    rcon = rcon_for(profile)
    hooks.handle_new_match_start(rcon, event(title, 1_000))
    layer = profile.parse_layer(map_id)
    loop = object.__new__(LogLoop)
    loop.rcon = rcon
    loop.ACTIVE_MAP_INDEX = 0
    loop.CURR_MAP_END = 0
    loop.now = 1_130
    loop.record_cap_flips = Mock()
    loop.record_player_stats = Mock()
    loop.get_detailed_players = Mock(return_value={"players": {}, "fail_count": 0})

    with pytest.raises(TimeoutError):
        loop.update_maps_history(0)
    assert history[0]["start"] == 1_000
    rcon.get_gamestate.side_effect = None
    rcon.get_gamestate.return_value = {
        "current_map": {"id": map_id},
        "game_mode": layer.game_mode,
        "match_time": 5_400,
        "time_remaining": timedelta(seconds=5_270),
    }
    assert loop.update_maps_history(0) == 130
    assert history[0]["name"] == layer.id
    assert history[0]["guessed"] is False
    assert history[0]["match_time"] == (
        9_000 if layer.game_mode == GameMode.OFFENSIVE else 5_400
    )
    loop.record_player_stats.assert_called_once()


@pytest.mark.parametrize(
    "profile,map_id,title,matches",
    [
        (HLL_PROFILE, "carentan_warfare_night", "CARENTAN Warfare", True),
        (HLL_PROFILE, "carentan_warfare_night", "CARENTAN DAY Warfare", False),
        (HLL_PROFILE, "carentan_warfare", "CARENTAN Conquest", False),
        (HLL_PROFILE, "carentan_warfare", "UTAH BEACH Warfare", False),
        (HLLV_PROFILE, "wdeva_offensivenva_day", "VẠN TƯỜNG US Offensive", False),
        (HLLV_PROFILE, "wdeva_offensivenva_day", "VẠN TƯỜNG Offensive", True),
        (HLL_PROFILE, "unknown", "UNKNOWN Warfare", False),
    ],
)
def test_log_layer_compatibility(profile, map_id, title, matches):
    layer = profile.parse_layer(map_id)
    assert layer_matches_match_log(layer, event(title, 1_000)["raw"]) is matches
