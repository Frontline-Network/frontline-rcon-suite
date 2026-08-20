from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "rcon" / "auto_settings_preview.py"
SPEC = spec_from_file_location("auto_settings_preview", MODULE_PATH)
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
analyze_auto_settings = MODULE.analyze_auto_settings


def _codes(issues):
    return [issue["code"] for issue in issues]


def test_preview_rejects_invalid_structure_without_guessing_values():
    result = analyze_auto_settings(
        {
            "always_apply_defaults": "yes",
            "defaults": [],
            "rules": {
                "conditions": {"player_count": {"min": 20, "max": 10}}
            },
        }
    )

    assert result["valid"] is False
    assert result["simulation_complete"] is False
    assert _codes(result["errors"]) == [
        "setting_must_be_boolean",
        "defaults_must_be_object",
        "rules_must_be_array",
    ]
    assert result["effective_commands"] == {}


def test_preview_marks_missing_scenario_values_as_unknown():
    result = analyze_auto_settings(
        {
            "defaults": {"set_vip_slots_num": {"value": 2}},
            "rules": [
                {
                    "conditions": {"player_count": {"min": 4, "max": 44}},
                    "commands": {"set_autobalance_threshold": {"max_diff": 0}},
                }
            ],
        }
    )

    assert result["valid"] is True
    assert result["simulation_complete"] is False
    assert result["rules"][0]["matches"] is None
    assert result["effective_commands"] == {}


def test_preview_uses_first_matching_rule_and_explains_effective_commands():
    settings = {
        "always_apply_defaults": True,
        "can_invoke_multiple_rules": False,
        "defaults": {
            "set_vip_slots_num": {"value": 2},
            "set_autobalance_threshold": {"max_diff": 2},
        },
        "rules": [
            {
                "conditions": {"player_count": {"min": 4, "max": 44}},
                "commands": {"set_autobalance_threshold": {"max_diff": 0}},
            },
            {
                "conditions": {"player_count": {"min": 40, "max": 100}},
                "commands": {"set_autobalance_threshold": {"max_diff": 1}},
            },
        ],
    }

    result = analyze_auto_settings(settings, scenario={"player_count": 42})

    assert result["valid"] is True
    assert result["simulation_complete"] is True
    assert result["matched_rule_indexes"] == [0]
    assert result["effective_commands"] == {
        "set_vip_slots_num": {"value": 2},
        "set_autobalance_threshold": {"max_diff": 0},
    }


def test_preview_can_combine_multiple_rules_in_priority_order():
    settings = {
        "can_invoke_multiple_rules": True,
        "rules": [
            {
                "conditions": {"player_count": {"min": 0, "max": 100}},
                "commands": {
                    "set_idle_autokick_time": {"minutes": 0},
                    "set_autobalance_threshold": {"max_diff": 0},
                },
            },
            {
                "conditions": {"player_count": {"min": 40, "max": 100}},
                "commands": {"set_autobalance_threshold": {"max_diff": 1}},
            },
        ],
    }

    result = analyze_auto_settings(settings, scenario={"player_count": 50})

    assert result["matched_rule_indexes"] == [0, 1]
    assert result["effective_commands"] == {
        "set_idle_autokick_time": {"minutes": 0},
        "set_autobalance_threshold": {"max_diff": 1},
    }


def test_preview_reports_duplicate_unknown_and_overlapping_map_rules():
    settings = {
        "rules": [
            {
                "conditions": {"player_count": {"min": 4, "max": 44}},
                "commands": {
                    "set_votemap_whitelist": {
                        "map_names": ["carentan_warfare", "carentan_warfare"]
                    }
                },
            },
            {
                "conditions": {"player_count": {"min": 40, "max": 100}},
                "commands": {
                    "set_votemap_whitelist": {
                        "map_names": ["hllv_unknown_layer"]
                    }
                },
            },
        ]
    }

    result = analyze_auto_settings(
        settings,
        scenario={"player_count": 42},
        known_map_ids={"carentan_warfare"},
    )

    assert result["valid"] is True
    assert _codes(result["warnings"]) == [
        "duplicate_map_ids",
        "map_ids_not_available_for_game",
        "overlapping_rule_commands",
    ]
    overlap = result["warnings"][2]
    assert overlap["details"] == {
        "earlier_rule": 0,
        "later_rule": 1,
        "commands": ["set_votemap_whitelist"],
    }


def test_preview_checks_current_map_conditions_against_selected_game_maps():
    result = analyze_auto_settings(
        {
            "rules": [
                {
                    "conditions": {
                        "current_map": {
                            "map_names": [
                                "foy_warfare",
                                "foy_warfare",
                                "hllv_map",
                            ]
                        }
                    },
                    "commands": {},
                }
            ]
        },
        scenario={"current_map": "foy_warfare"},
        known_map_ids={"foy_warfare"},
    )

    assert _codes(result["warnings"]) == [
        "duplicate_map_ids",
        "map_ids_not_available_for_game",
    ]


def test_preview_supports_negated_maps_and_time_ranges_across_midnight():
    settings = {
        "rules": [
            {
                "conditions": {
                    "current_map": {
                        "map_names": ["carentan_warfare"],
                        "not": True,
                    },
                    "time_of_day": {"min": "22:00", "max": "04:00"},
                },
                "commands": {"set_vip_slots_num": {"value": 2}},
            }
        ]
    }

    result = analyze_auto_settings(
        settings,
        scenario={"current_map": "foy_warfare", "time_of_day": "01:30"},
    )

    assert result["simulation_complete"] is True
    assert result["matched_rule_indexes"] == [0]


def test_preview_does_not_mutate_the_configuration():
    settings = {
        "always_apply_defaults": True,
        "defaults": {"set_vip_slots_num": {"value": 2}},
        "rules": [],
    }
    original = deepcopy(settings)

    result = analyze_auto_settings(settings)
    result["effective_commands"]["set_vip_slots_num"]["value"] = 0

    assert settings == original
