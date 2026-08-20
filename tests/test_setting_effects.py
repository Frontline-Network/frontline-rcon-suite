import json
from datetime import UTC, datetime
from types import SimpleNamespace

from rcon.setting_effects import (
    GENERAL_SETTING_EFFECTS,
    analyze_auto_settings_management,
    build_setting_effects_snapshot,
    summarize_setting_audits,
)

NOW = datetime(2026, 8, 20, 12, 30, tzinfo=UTC)


class FakeUser:
    def __init__(self, permissions=(), *, superuser=False):
        self.permissions = set(permissions)
        self.is_superuser = superuser

    def has_perm(self, permission):
        return permission in self.permissions


class FakeRcon:
    def __init__(self, values=None, failing=()):
        self.values = values or {
            key: index for index, key in enumerate(GENERAL_SETTING_EFFECTS, start=1)
        }
        self.failing = set(failing)
        self.calls = []

    def __getattr__(self, name):
        for key, metadata in GENERAL_SETTING_EFFECTS.items():
            if metadata["getter"] == name:

                def getter(setting_key=key):
                    self.calls.append(setting_key)
                    if setting_key in self.failing:
                        raise ConnectionError("secret-internal-host:1234")
                    return self.values[setting_key]

                return getter
        raise AttributeError(name)


def all_permissions(*, audit=True, auto_settings=True):
    permissions = set()
    for metadata in GENERAL_SETTING_EFFECTS.values():
        permissions.add(metadata["view_permission"])
        permissions.add(metadata["change_permission"])
        restore = metadata.get("restore")
        if restore:
            permissions.add(restore["permission"])
    if audit:
        permissions.add("api.can_view_audit_logs")
    if auto_settings:
        permissions.add("api.can_view_auto_settings")
    return permissions


def item(snapshot, key):
    return next(entry for entry in snapshot["settings"] if entry["key"] == key)


def test_metadata_contract_is_complete_and_unambiguous():
    assert len(GENERAL_SETTING_EFFECTS) == 9
    assert len({entry["getter"] for entry in GENERAL_SETTING_EFFECTS.values()}) == 9
    assert len({entry["setter"] for entry in GENERAL_SETTING_EFFECTS.values()}) == 9
    for key, metadata in GENERAL_SETTING_EFFECTS.items():
        assert metadata["getter"] == f"get_{key}"
        assert metadata["setter"] == f"set_{key}"
        assert metadata["view_permission"].startswith("api.can_view_")
        assert metadata["change_permission"].startswith("api.can_change_")
        assert metadata["side_effects"]
        assert metadata["conflicts"]
        assert metadata["recommended"]["state"] in {"known", "unknown"}


def test_full_snapshot_is_versioned_and_explicit_for_both_games():
    rcon = FakeRcon()
    snapshot = build_setting_effects_snapshot(
        rcon_api=rcon,
        user=FakeUser(all_permissions()),
        server_number=3,
        game="hllv",
        auto_settings={},
        auto_settings_state="available",
        audit_state="available",
        generated_at=NOW,
    )

    assert snapshot["schema_version"] == 1
    assert snapshot["server_number"] == 3
    assert snapshot["game"] == "hllv"
    assert snapshot["health"] == "available"
    assert snapshot["visibility"] == "full"
    assert len(snapshot["settings"]) == len(GENERAL_SETTING_EFFECTS)
    assert rcon.calls == list(GENERAL_SETTING_EFFECTS)
    assert all(
        setting["compatibility"]["games"] == {"hll": "supported", "hllv": "supported"}
        for setting in snapshot["settings"]
    )
    assert json.loads(json.dumps(snapshot))["schema_version"] == 1


def test_no_view_permissions_produce_no_rcon_calls_and_unknown_health():
    rcon = FakeRcon()
    snapshot = build_setting_effects_snapshot(
        rcon_api=rcon,
        user=FakeUser(),
        server_number=1,
        game="hll",
        generated_at=NOW,
    )

    assert rcon.calls == []
    assert snapshot["visibility"] == "none"
    assert snapshot["health"] == "unknown"
    assert all(
        setting["effective"]["state"] == "permission_missing"
        for setting in snapshot["settings"]
    )


def test_missing_view_permission_never_calls_or_exposes_setting_value():
    allowed = GENERAL_SETTING_EFFECTS["queue_length"]["view_permission"]
    rcon = FakeRcon()
    snapshot = build_setting_effects_snapshot(
        rcon_api=rcon,
        user=FakeUser({allowed}),
        server_number=1,
        game="hll",
        generated_at=NOW,
    )

    assert rcon.calls == ["queue_length"]
    hidden = item(snapshot, "vip_slots_num")
    assert hidden["visibility"] == "permission_missing"
    assert hidden["configured"] == {"state": "permission_missing", "value": None}
    assert hidden["effective"] == {"state": "permission_missing", "value": None}
    assert hidden["next_action"] == "request_view_permission"
    assert snapshot["visibility"] == "partial"


def test_one_failed_getter_yields_partial_sanitized_result():
    rcon = FakeRcon(failing={"vip_slots_num"})
    snapshot = build_setting_effects_snapshot(
        rcon_api=rcon,
        user=FakeUser(all_permissions()),
        server_number=1,
        game="hll",
        generated_at=NOW,
    )

    failed = item(snapshot, "vip_slots_num")
    assert snapshot["health"] == "partial"
    assert failed["effective"]["state"] == "unavailable"
    assert failed["next_action"] == "check_game_server_connection"
    assert "secret-internal-host" not in str(snapshot)
    assert item(snapshot, "queue_length")["effective"]["state"] == "observed"


def test_unknown_game_never_inherits_hll_compatibility():
    snapshot = build_setting_effects_snapshot(
        rcon_api=FakeRcon(),
        user=FakeUser(all_permissions()),
        server_number=9,
        game="future-game",
        generated_at=NOW,
    )

    assert snapshot["game"] == "unknown"
    assert all(
        setting["compatibility"]["current_state"] == "unknown"
        for setting in snapshot["settings"]
    )


def test_auto_settings_candidates_do_not_claim_an_active_rule():
    managed = analyze_auto_settings_management(
        {
            "defaults": {"set_vip_slots_num": {"value": 2}},
            "rules": [
                {
                    "conditions": {"player_count": {"min": 45}},
                    "commands": {"set_vip_slots_num": {"value": 0}},
                }
            ],
        }
    )

    assert managed["vip_slots_num"] == {
        "managed": True,
        "candidates": [
            {"source": "defaults", "value_state": "known", "value": 2},
            {"source": "rule:0", "value_state": "known", "value": 0},
        ],
    }
    assert managed["queue_length"] == {"managed": False, "candidates": []}
    assert "active" not in str(managed["vip_slots_num"])


def test_audit_summary_separates_failed_attempt_from_successful_change():
    records = [
        SimpleNamespace(
            id=12,
            username="Alex",
            creation_time=NOW,
            command="set_vip_slots_num",
            command_result='{"failed": true}',
        ),
        SimpleNamespace(
            id=11,
            username="Pingu",
            creation_time=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
            command="set_vip_slots_num",
            command_result='{"failed": false}',
        ),
    ]

    summary = summarize_setting_audits(records, ["set_vip_slots_num"])

    assert summary["set_vip_slots_num"]["last_attempt"] == {
        "audit_id": 12,
        "actor": "Alex",
        "at": "2026-08-20T12:30:00Z",
        "outcome": "failed",
    }
    assert summary["set_vip_slots_num"]["last_successful_change"] == {
        "audit_id": 11,
        "actor": "Pingu",
        "at": "2026-08-20T12:00:00Z",
    }


def test_audit_false_result_or_error_is_not_treated_as_a_change():
    records = [
        SimpleNamespace(
            id=14,
            username="Alex",
            creation_time=NOW,
            command="set_vip_slots_num",
            command_result='{"failed": false, "error": "validation"}',
        ),
        SimpleNamespace(
            id=13,
            username="Pingu",
            creation_time=NOW,
            command="set_vip_slots_num",
            command_result='{"failed": false, "result": false}',
        ),
    ]

    summary = summarize_setting_audits(records, ["set_vip_slots_num"])

    assert summary["set_vip_slots_num"]["last_attempt"]["outcome"] == "failed"
    assert summary["set_vip_slots_num"]["last_successful_change"] is None


def test_audit_and_automation_details_remain_permission_aware():
    snapshot = build_setting_effects_snapshot(
        rcon_api=FakeRcon(),
        user=FakeUser(all_permissions(audit=False, auto_settings=False)),
        server_number=2,
        game="hll",
        auto_settings={"defaults": {"set_vip_slots_num": {"value": 2}}},
        auto_settings_state="permission_missing",
        audit_summaries={
            "set_vip_slots_num": {
                "last_attempt": {"actor": "Hidden"},
                "last_successful_change": {"actor": "Hidden"},
            }
        },
        audit_state="permission_missing",
        generated_at=NOW,
    )

    vip = item(snapshot, "vip_slots_num")
    assert vip["audit"]["state"] == "permission_missing"
    assert vip["audit"]["last_attempt"] is None
    assert vip["automation"]["state"] == "permission_missing"
    assert vip["automation"] == {
        "state": "permission_missing",
        "managed": False,
        "candidates": [],
    }


def test_audit_backend_failure_is_not_reported_as_no_history():
    snapshot = build_setting_effects_snapshot(
        rcon_api=FakeRcon(),
        user=FakeUser(all_permissions()),
        server_number=2,
        game="hll",
        audit_summaries={},
        audit_state="unavailable",
        generated_at=NOW,
    )

    vip = item(snapshot, "vip_slots_num")
    assert vip["audit"]["state"] == "unavailable"
    assert vip["audit"]["last_attempt"] is None
    assert vip["audit"]["last_successful_change"] is None


def test_restore_is_distinct_from_recommendation_and_permission_checked():
    user = FakeUser(all_permissions())
    snapshot = build_setting_effects_snapshot(
        rcon_api=FakeRcon(),
        user=user,
        server_number=1,
        game="hll",
        generated_at=NOW,
    )

    thresholds = item(snapshot, "votekick_thresholds")
    vip = item(snapshot, "vip_slots_num")
    assert thresholds["restore"] == {
        "supported": True,
        "command": "reset_votekick_thresholds",
        "permission": "api.can_reset_votekick_threshold",
        "allowed": True,
    }
    assert vip["recommended"] == {"state": "known", "value": 2}
    assert vip["restore"]["supported"] is False


def test_change_and_restore_are_blocked_without_view_permission():
    permissions = {
        GENERAL_SETTING_EFFECTS["votekick_thresholds"]["change_permission"],
        GENERAL_SETTING_EFFECTS["votekick_thresholds"]["restore"]["permission"],
    }
    snapshot = build_setting_effects_snapshot(
        rcon_api=FakeRcon(),
        user=FakeUser(permissions),
        server_number=1,
        game="hll",
        generated_at=NOW,
    )

    thresholds = item(snapshot, "votekick_thresholds")
    assert thresholds["change"]["permission_granted"] is True
    assert thresholds["change"]["allowed"] is False
    assert thresholds["change"]["blocked_reason"] == "missing_view_permission"
    assert thresholds["restore"]["allowed"] is False
