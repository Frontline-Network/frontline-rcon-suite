from datetime import datetime, timedelta, timezone

import pytest

from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rconweb.api import eventador_control_contract as contract

EVENT_ID = "10000000-0000-4000-8000-000000000001"
IDEMPOTENCY_KEY = "20000000-0000-4000-8000-000000000001"
NOW = datetime(2026, 9, 18, 18, 14, 55, tzinfo=timezone.utc)


class FakeHistory:
    def get_current_map(self):
        return {
            "name": "wdeve_warfare_day",
            "start": 1_789_752_600,
            "end": None,
        }


class FakeRcon:
    def __init__(self, profile=HLLV_PROFILE):
        self.game_profile = profile
        self.calls = []

    def get_status(self):
        return {
            "current_players": 2,
            "server_number": 1,
            "game": "hllv" if self.game_profile is HLLV_PROFILE else "hll",
            "map": "wdeve_warfare_day",
        }

    def get_players(self):
        return []

    def get_map(self):
        return "wdeve_warfare_day"

    def get_all_player_info(self):
        return [
            {"iD": "steam:2", "team": 2},
            {"iD": "steam:1", "team": 1},
        ]

    def set_broadcast(self, message):
        self.calls.append(("set_broadcast", message))

    def message_player(self, player_id, message):
        self.calls.append(("message_player", player_id, message))
        return True

    def set_map(self, map_id):
        self.calls.append(("set_map", map_id))

    def switch_player_now(self, player_id):
        self.calls.append(("switch_player_now", player_id))
        return True


@pytest.fixture(autouse=True)
def fixed_runtime(monkeypatch):
    monkeypatch.setattr(contract, "MapsHistory", FakeHistory)
    monkeypatch.setattr(contract, "get_server_number", lambda: "1")


def state(api=None):
    return contract.build_state(api or FakeRcon(), captured_at=NOW)


def plan(action="set_map", arguments=None):
    observed = state()
    return {
        "schema_version": 1,
        "event_id": EVENT_ID,
        "event_revision": 4,
        "workflow_revision": 2,
        "step_id": "round-1-map",
        "idempotency_key": IDEMPOTENCY_KEY,
        "execute_at": "2026-09-18T18:15:00.000Z",
        "target": {"server_number": 1, "game": "hllv"},
        "action": action,
        "reason": "Start approved first round",
        "arguments": (
            arguments if arguments is not None else {"map": "wdevd_warfare_day"}
        ),
        "expected": {
            "map": observed["map"],
            "round_id": observed["round_id"],
            "roster_hash": observed["roster_hash"],
            "state_observed_at": observed["captured_at"],
            "previous_step_id": None,
        },
    }


@pytest.mark.parametrize("profile,game", [(HLL_PROFILE, "hll"), (HLLV_PROFILE, "hllv")])
def test_capabilities_are_exact_and_disabled_by_default(profile, game):
    result = contract.build_capabilities(FakeRcon(profile), execution_enabled=False)

    assert result["schema_version"] == 1
    assert result["game"] == game
    assert result["execution_enabled"] is False
    assert set(result["actions"]) == set(contract.ACTION_REQUIREMENTS)
    assert result["actions"]["observe"]["mutates_game"] is False
    assert all(result["actions"][name]["available"] for name in result["actions"])
    assert result["interface"]["authentication"] == "dedicated_api_key_and_permission"
    assert result["limits"] == {
        "max_players_per_step": 100,
        "max_message_characters": 500,
        "prepare_ttl_seconds": 300,
    }


def test_unavailable_legacy_command_disables_capability_and_preparation_scope():
    api = FakeRcon()
    api.message_player = None
    frozen = plan("message_players", {"message": "Ready", "player_ids": ["steam:1"]})

    capabilities = contract.build_capabilities(api, execution_enabled=True)

    assert capabilities["actions"]["message_players"]["available"] is False
    assert not contract.runtime_scope_matches(api, state(api), frozen)


def test_state_projects_only_stable_ids_and_hashes():
    result = state()

    assert result["captured_at"] == "2026-09-18T18:14:55Z"
    assert result["map"] == "wdeve_warfare_day"
    assert len(result["round_id"]) == 64
    assert len(result["roster_hash"]) == 64
    assert list(result["players"]) == ["steam:1", "steam:2"]
    assert result["players"] == {
        "steam:1": {"player_id": "steam:1", "team": "allies"},
        "steam:2": {"player_id": "steam:2", "team": "axis"},
    }
    assert result["status"] == {
        "server_number": 1,
        "game": "hllv",
        "current_players": 2,
    }


def test_state_fails_closed_without_a_stable_round_identity(monkeypatch):
    class MissingHistory:
        def get_current_map(self):
            return None

    monkeypatch.setattr(contract, "MapsHistory", MissingHistory)

    with pytest.raises(contract.ContractError, match="round identity"):
        state()


def test_plan_validation_rejects_drift_raw_commands_and_duplicate_targets():
    valid = plan()
    assert contract.validate_plan(valid) is valid
    with pytest.raises(contract.ContractError, match="exactly"):
        contract.validate_plan({**valid, "extra": True})
    with pytest.raises(contract.ContractError, match="not allowed"):
        contract.validate_plan({**valid, "action": "raw_command"})
    with pytest.raises(contract.ContractError, match="duplicates"):
        contract.validate_plan(
            plan(
                "message_players",
                {"message": "Hello", "player_ids": ["steam:1", "steam:1"]},
            )
        )
    restart = plan("restart_round", {"map": "wdevd_warfare_day"})
    with pytest.raises(contract.ContractError, match="must match"):
        contract.validate_plan(restart)


def test_state_binding_detects_map_roster_and_target_changes():
    observed = state()
    frozen = plan()
    assert contract.state_matches_plan(observed, frozen)
    assert not contract.state_matches_plan({**observed, "map": "Other"}, frozen)
    assert not contract.state_matches_plan(
        {**observed, "roster_hash": "f" * 64}, frozen
    )
    changed_status = {**observed["status"], "server_number": 2}
    assert not contract.state_matches_plan(
        {**observed, "status": changed_status}, frozen
    )


def test_runtime_scope_requires_live_players_and_the_wrong_current_side():
    api = FakeRcon()
    observed = state(api)
    direct = plan("message_players", {"message": "Ready", "player_ids": ["steam:1"]})
    assert contract.runtime_scope_matches(api, observed, direct)
    missing = plan(
        "message_players", {"message": "Ready", "player_ids": ["steam:missing"]}
    )
    assert not contract.runtime_scope_matches(api, observed, missing)
    switch = plan(
        "switch_players",
        {"players": [{"player_id": "steam:1", "target_team": "axis"}]},
    )
    assert contract.runtime_scope_matches(api, observed, switch)
    already_correct = plan(
        "switch_players",
        {"players": [{"player_id": "steam:1", "target_team": "allies"}]},
    )
    assert not contract.runtime_scope_matches(api, observed, already_correct)


def test_runtime_scope_rejects_unknown_layer_ids():
    api = FakeRcon()
    observed = state(api)
    unknown = plan("set_map", {"map": "Warfare-Smolensk"})

    assert not contract.runtime_scope_matches(api, observed, unknown)


@pytest.mark.parametrize(
    "profile,layer_id",
    [
        (HLL_PROFILE, "carentan_warfare"),
        (HLLV_PROFILE, "wdevd_warfare_day"),
    ],
)
def test_runtime_scope_accepts_known_layers_for_both_games(profile, layer_id):
    api = FakeRcon(profile)

    assert contract.runtime_scope_matches(
        api,
        state(api),
        plan("set_map", {"map": layer_id}),
    )


def test_schedule_window_rejects_stale_and_far_future_steps():
    assert contract.schedule_conflict(NOW, NOW) is None
    assert (
        contract.schedule_conflict(NOW, NOW - timedelta(seconds=31))
        == "execution_window_expired"
    )
    assert (
        contract.schedule_conflict(NOW, NOW + timedelta(seconds=301))
        == "execution_window_too_far"
    )


@pytest.mark.parametrize(
    "action,arguments,expected_call",
    [
        ("broadcast", {"message": "Event starts"}, ("set_broadcast", "Event starts")),
        (
            "message_players",
            {"message": "Ready", "player_ids": ["steam:1"]},
            ("message_player", "steam:1", "Ready"),
        ),
        (
            "set_map",
            {"map": "wdevd_warfare_day"},
            ("set_map", "wdevd_warfare_day"),
        ),
        (
            "switch_players",
            {"players": [{"player_id": "steam:1", "target_team": "axis"}]},
            ("switch_player_now", "steam:1"),
        ),
        (
            "set_pause",
            {"status": "paused", "message": "Event paused"},
            ("set_broadcast", "Event paused"),
        ),
    ],
)
def test_execution_maps_only_allowlisted_actions(action, arguments, expected_call):
    api = FakeRcon()
    frozen = plan(action, arguments)
    if action == "set_map":
        contract.validate_plan(frozen)
    else:
        contract.validate_plan(frozen)

    result = contract.execute_game_action(api, frozen)

    assert result["action"] == action
    assert result["targets"][0]["status"] == "succeeded"
    assert api.calls == [expected_call]


def test_observe_never_contacts_a_mutating_command():
    api = FakeRcon()
    frozen = plan("observe", {})
    contract.validate_plan(frozen)

    assert contract.execute_game_action(api, frozen) == {
        "action": "observe",
        "targets": [{"kind": "server", "status": "succeeded"}],
    }
    assert api.calls == []


def test_bulk_rejection_keeps_per_player_results_and_stops_remaining_targets():
    api = FakeRcon()
    api.message_player = lambda player_id, message: player_id != "steam:2"
    frozen = plan(
        "message_players",
        {
            "message": "Ready",
            "player_ids": ["steam:1", "steam:2", "steam:3"],
        },
    )
    contract.validate_plan(frozen)

    with pytest.raises(contract.KnownActionFailure) as raised:
        contract.execute_game_action(api, frozen)

    assert raised.value.result == {
        "action": "message_players",
        "targets": [
            {"player_id": "steam:1", "status": "succeeded"},
            {"player_id": "steam:2", "status": "failed"},
            {"player_id": "steam:3", "status": "not_attempted"},
        ],
    }
