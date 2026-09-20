"""No real RCON, Redis or player actions: recipient, throttle and roster regressions."""

import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rcon.autobalancer import snapshot as snapshots
from rcon.autobalancer.feedback import ended_message
from rcon.autobalancer.models import Phase
from rcon.autobalancer.store import AutobalancerStore
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from tests.autobalancer.test_service import service, make_snapshot
from tests.autobalancer.test_store import FakeRedis
from tests.autobalancer.test_volunteer_flow import invitation, config, at


@pytest.mark.parametrize(
    "phase", [Phase.VOLUNTEER, Phase.PROPOSED, Phase.ARMED, Phase.VERIFYING]
)
def test_only_participants_and_announced_candidates_receive_one_abort(phase):
    instance = service()
    state = invitation(
        phase=phase,
        volunteers=["v"],
        pending_volunteers={"pending": {}},
        candidate={"player_id": "candidate"},
    )
    instance._notify_ended(state, "Teamzählungen stimmen nicht überein")
    expected = {"v", "pending"} | (
        {"candidate"} if phase in {Phase.ARMED, Phase.VERIFYING} else set()
    )
    assert {p for p, _ in instance.rcon.messages} == expected
    assert all(
        "Spielerzahlen" not in m and "Vormerkung" not in m
        for _, m in instance.rcon.messages
    )
    assert all(
        ("Admin" in m) == (phase == Phase.VERIFYING) for _, m in instance.rcon.messages
    )
    instance._notify_ended(state, "again")
    assert len(instance.rcon.messages) == len(expected)


def test_invitees_who_never_replied_receive_no_cancellation():
    instance = service()
    instance._notify_ended(invitation(), "Teamzählungen stimmen nicht überein")
    assert instance.rcon.messages == []


def test_uncertain_switch_never_promises_player_stays_in_team():
    assert "Admin" in ended_message("Teamwechsel wurde nicht bestätigt")
    assert "Du bleibst" not in ended_message("Teamwechsel wurde nicht bestätigt")


def test_invitation_reservation_survives_state_restart_and_is_server_scoped():
    redis = FakeRedis()
    redis.set = Mock(wraps=redis.set)
    first = AutobalancerStore(redis, server_number=3)
    second = AutobalancerStore(redis, server_number=4)
    assert first.claim_volunteer_invitation("p")
    key = redis.set.call_args.args[0]
    assert redis.set.call_args.kwargs == {"nx": True, "ex": 300}
    first.clear_runtime_state()
    assert not AutobalancerStore(redis, server_number=3).claim_volunteer_invitation("p")
    assert second.claim_volunteer_invitation("p")
    redis.delete(key)  # Redis TTL expiry permits the next invitation.
    assert first.claim_volunteer_invitation("p")


@pytest.mark.parametrize("fails", [False, True])
def test_new_incidents_do_not_repeat_invites_even_after_uncertain_send(fails):
    instance = service()
    attempts = []

    def send(pid, **kwargs):
        attempts.append(pid)
        if fails:
            raise TimeoutError("ambiguous")
        return True

    instance.rcon.message_player = send
    instance._request_volunteers({}, make_snapshot(at()), config())
    instance._request_volunteers({}, make_snapshot(at()), config())
    assert sorted(attempts) == ["a0", "a1", "a2", "a3"]


@pytest.fixture(params=[HLL_PROFILE, HLLV_PROFILE], ids=["HLL", "HLLV"])
def roster_api(request, monkeypatch):
    now = 2000000000.0
    monkeypatch.setattr(snapshots.time, "time", lambda: now)
    monkeypatch.setattr(
        snapshots, "_current_round", lambda *a: ("1000:test", 1000, True)
    )
    profiles = Mock(return_value=[{"player_id": "a", "current_playtime_seconds": 900}])
    monkeypatch.setattr(snapshots, "get_live_profiles", profiles)
    rows = [
        {"iD": "a", "name": "A", "team": 1, "role": 9, "platoon": "Able"},
        {"iD": "new", "name": "New", "team": 1, "role": 0, "platoon": "Able"},
    ]
    sample = {"captured_at": now, "players": rows}
    state = {
        "current_map": {"id": "test"},
        "num_allied_players": 2,
        "num_axis_players": 0,
        "time_remaining": timedelta(hours=1),
    }
    api = SimpleNamespace(
        game_profile=request.param,
        get_gamestate=Mock(return_value=state),
        get_raw_player_snapshot=Mock(return_value=sample),
        get_team_view=Mock(side_effect=AssertionError("UI roster used")),
        get_players=Mock(side_effect=AssertionError("old ID list used")),
        get_autobalance_enabled=lambda: True,
        get_autobalance_threshold=lambda: 2,
    )
    store = SimpleNamespace(
        track_squad_memberships=lambda r, ids, n: {pid: 600 for pid in ids}
    )
    return api, store, profiles, now


def build(data):
    api, store, _, now = data
    return snapshots.build_snapshot(
        api, store, datetime.fromtimestamp(now, timezone.utc)
    )


def test_missing_profile_never_removes_player_from_counts(roster_api):
    result = build(roster_api)
    assert result.counts_match and len(result.players) == 2
    assert result.players[0].is_leader
    assert result.players[0].connected_seconds == 900
    assert result.players[1].connected_seconds == 0  # Not assumed eligible.
    assert result.players[1].unit_size == 2
    roster_api[0].get_team_view.assert_not_called()
    roster_api[2].assert_called_once_with(["a", "new"])


@pytest.mark.parametrize("recovery", [True, False])
def test_counts_require_exact_independent_match_after_one_refresh(roster_api, recovery):
    api = roster_api[0]
    correct = api.get_gamestate.return_value
    mismatch = dict(correct, num_allied_players=3)
    api.get_gamestate.side_effect = [mismatch, correct if recovery else mismatch]
    result = build(roster_api)
    assert result.counts_match is recovery
    assert api.get_raw_player_snapshot.call_count == 2
    api.get_gamestate.clear_for.assert_called_once_with()
    api.get_raw_player_snapshot.clear_for.assert_called_once_with()


@pytest.mark.parametrize(
    "bad",
    ["duplicate", "missing_id", "stale", "future", "nan", "incomplete", "bad_row"],
)
def test_invalid_roster_fails_closed(roster_api, bad):
    sample = roster_api[0].get_raw_player_snapshot.return_value
    if bad == "duplicate":
        sample["players"].append(deepcopy(sample["players"][0]))
    elif bad == "missing_id":
        sample["players"][0].pop("iD")
    elif bad == "stale":
        sample["captured_at"] -= 11
    elif bad == "future":
        sample["captured_at"] += 1
    elif bad == "nan":
        sample["captured_at"] = float("nan")
    elif bad == "incomplete":
        sample["players"] = None
    else:
        sample["players"][0] = None
    with pytest.raises(ValueError):
        build(roster_api)


def test_roster_expiring_during_profile_load_blocks_balance(roster_api, monkeypatch):
    profiles = roster_api[2]

    def slow(ids):
        monkeypatch.setattr(snapshots.time, "time", lambda: roster_api[3] + 11)
        return []

    profiles.side_effect = slow
    assert not build(roster_api).counts_match
