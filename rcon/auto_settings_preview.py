"""Pure validation and dry-run helpers for Auto Settings configurations.

The preview intentionally has no RCON dependency.  It can therefore be used by
the API and future form-based editors without sending a game-server command.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


SUPPORTED_CONDITIONS = {
    "player_count",
    "online_mods",
    "ingame_mods",
    "current_map",
    "time_of_day",
}


def _issue(code: str, path: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "path": path, "details": details}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_hhmm(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    if value == "24:00":
        return 24 * 60
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        return None
    return parsed.hour * 60 + parsed.minute


def _range_matches(value: Any, params: dict[str, Any]) -> bool | None:
    if not _is_number(value):
        return None
    minimum = params.get("min", float("-inf"))
    maximum = params.get("max", float("inf"))
    if not _is_number(minimum) or not _is_number(maximum):
        return None
    return minimum <= value <= maximum


def _time_matches(value: Any, params: dict[str, Any]) -> bool | None:
    current = _parse_hhmm(value)
    minimum = _parse_hhmm(params.get("min", "00:00"))
    maximum = _parse_hhmm(params.get("max", "23:59"))
    if current is None or minimum is None or maximum is None:
        return None
    if minimum <= maximum:
        return minimum <= current <= maximum
    return current >= minimum or current <= maximum


def _condition_matches(
    name: str, params: dict[str, Any], scenario: dict[str, Any]
) -> bool | None:
    if name in {"player_count", "online_mods", "ingame_mods"}:
        matched = _range_matches(scenario.get(name), params)
    elif name == "current_map":
        current_map = scenario.get("current_map")
        map_names = params.get("map_names")
        matched = (
            current_map in map_names
            if isinstance(current_map, str) and isinstance(map_names, list)
            else None
        )
    elif name == "time_of_day":
        matched = _time_matches(scenario.get("time_of_day"), params)
    else:
        matched = None

    if matched is not None and params.get("not") is True:
        return not matched
    return matched


def _validate_condition(
    name: str,
    params: Any,
    path: str,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    known_map_ids: set[str] | None,
) -> None:
    if name not in SUPPORTED_CONDITIONS:
        errors.append(_issue("unknown_condition", path, condition=name))
        return
    if not isinstance(params, dict):
        errors.append(_issue("condition_parameters_must_be_object", path))
        return
    if "not" in params and not isinstance(params["not"], bool):
        errors.append(_issue("condition_not_must_be_boolean", f"{path}.not"))

    if name in {"player_count", "online_mods", "ingame_mods"}:
        minimum = params.get("min", 0)
        maximum = params.get("max", 100)
        if not _is_number(minimum) or not _is_number(maximum):
            errors.append(_issue("condition_range_must_be_numeric", path))
        elif minimum > maximum:
            errors.append(
                _issue(
                    "condition_min_exceeds_max",
                    path,
                    minimum=minimum,
                    maximum=maximum,
                )
            )
        elif minimum < 0 or maximum > 100:
            errors.append(
                _issue(
                    "condition_range_out_of_bounds",
                    path,
                    minimum=minimum,
                    maximum=maximum,
                    allowed_minimum=0,
                    allowed_maximum=100,
                )
            )
    elif name == "current_map":
        map_names = params.get("map_names")
        if not isinstance(map_names, list) or not all(
            isinstance(map_name, str) and map_name for map_name in map_names
        ):
            errors.append(_issue("condition_map_names_must_be_string_list", path))
        else:
            duplicates = sorted(
                {
                    map_name
                    for map_name in map_names
                    if map_names.count(map_name) > 1
                }
            )
            if duplicates:
                warnings.append(
                    _issue(
                        "duplicate_map_ids",
                        f"{path}.map_names",
                        map_ids=duplicates,
                    )
                )
            if known_map_ids is not None:
                unknown = sorted(set(map_names) - known_map_ids)
                if unknown:
                    warnings.append(
                        _issue(
                            "map_ids_not_available_for_game",
                            f"{path}.map_names",
                            map_ids=unknown,
                        )
                    )
    elif name == "time_of_day":
        for field, default in (("min", "00:00"), ("max", "23:59")):
            if _parse_hhmm(params.get(field, default)) is None:
                errors.append(
                    _issue("condition_time_must_be_hhmm", f"{path}.{field}")
                )


def _check_map_lists(
    commands: dict[str, Any],
    path: str,
    warnings: list[dict[str, Any]],
    known_map_ids: set[str] | None,
) -> None:
    for command_name, command_params in commands.items():
        if not isinstance(command_params, dict):
            continue
        map_names = command_params.get("map_names")
        if not isinstance(map_names, list):
            continue

        duplicates = sorted(
            {map_name for map_name in map_names if map_names.count(map_name) > 1}
        )
        if duplicates:
            warnings.append(
                _issue(
                    "duplicate_map_ids",
                    f"{path}.{command_name}.map_names",
                    map_ids=duplicates,
                )
            )
        if known_map_ids is not None:
            unknown = sorted(
                {
                    map_name
                    for map_name in map_names
                    if isinstance(map_name, str) and map_name not in known_map_ids
                }
            )
            if unknown:
                warnings.append(
                    _issue(
                        "map_ids_not_available_for_game",
                        f"{path}.{command_name}.map_names",
                        map_ids=unknown,
                    )
                )


def _player_range(rule: dict[str, Any]) -> tuple[float, float] | None:
    params = rule.get("conditions", {}).get("player_count")
    if not isinstance(params, dict) or params.get("not") is True:
        return None
    minimum = params.get("min", 0)
    maximum = params.get("max", 100)
    if not _is_number(minimum) or not _is_number(maximum) or minimum > maximum:
        return None
    return float(minimum), float(maximum)


def _check_overlaps(
    rules: list[dict[str, Any]], warnings: list[dict[str, Any]]
) -> None:
    for left_position, left_rule in enumerate(rules):
        left_range = _player_range(left_rule)
        if left_range is None:
            continue
        for right_position in range(left_position + 1, len(rules)):
            right_rule = rules[right_position]
            right_range = _player_range(right_rule)
            if right_range is None:
                continue
            if max(left_range[0], right_range[0]) > min(
                left_range[1], right_range[1]
            ):
                continue
            shared_commands = sorted(
                set(left_rule.get("commands", {}))
                & set(right_rule.get("commands", {}))
            )
            conflicting = [
                command
                for command in shared_commands
                if left_rule["commands"].get(command)
                != right_rule["commands"].get(command)
            ]
            if conflicting:
                warnings.append(
                    _issue(
                        "overlapping_rule_commands",
                        f"rules[{right_rule['index']}]",
                        earlier_rule=left_rule["index"],
                        later_rule=right_rule["index"],
                        commands=conflicting,
                    )
                )


def analyze_auto_settings(
    settings: Any,
    *,
    scenario: dict[str, Any] | None = None,
    known_map_ids: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Validate and dry-run an Auto Settings configuration.

    ``scenario`` is explicit input rather than live server state.  Missing
    values are reported as unknown and never guessed.
    """

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    scenario = scenario if isinstance(scenario, dict) else {}
    known_maps = set(known_map_ids) if known_map_ids is not None else None

    if not isinstance(settings, dict):
        return {
            "valid": False,
            "simulation_complete": False,
            "errors": [_issue("settings_must_be_object", "$")],
            "warnings": [],
            "rules": [],
            "matched_rule_indexes": [],
            "effective_commands": {},
        }

    for key in ("always_apply_defaults", "can_invoke_multiple_rules"):
        if key in settings and not isinstance(settings[key], bool):
            errors.append(_issue("setting_must_be_boolean", key))

    defaults = settings.get("defaults", {})
    if not isinstance(defaults, dict):
        errors.append(_issue("defaults_must_be_object", "defaults"))
        defaults = {}
    else:
        _check_map_lists(defaults, "defaults", warnings, known_maps)

    raw_rules = settings.get("rules", [])
    if not isinstance(raw_rules, list):
        errors.append(_issue("rules_must_be_array", "rules"))
        raw_rules = []

    normalized_rules: list[dict[str, Any]] = []
    rule_results: list[dict[str, Any]] = []
    for index, raw_rule in enumerate(raw_rules):
        path = f"rules[{index}]"
        if not isinstance(raw_rule, dict):
            errors.append(_issue("rule_must_be_object", path))
            continue
        conditions = raw_rule.get("conditions", {})
        commands = raw_rule.get("commands", {})
        if not isinstance(conditions, dict):
            errors.append(_issue("conditions_must_be_object", f"{path}.conditions"))
            conditions = {}
        if not isinstance(commands, dict):
            errors.append(_issue("commands_must_be_object", f"{path}.commands"))
            commands = {}
        _check_map_lists(commands, f"{path}.commands", warnings, known_maps)
        for name, params in conditions.items():
            _validate_condition(
                name,
                params,
                f"{path}.conditions.{name}",
                errors,
                warnings,
                known_maps,
            )

        normalized_rule = {
            "index": index,
            "conditions": conditions,
            "commands": commands,
        }
        normalized_rules.append(normalized_rule)
        condition_results = [
            {
                "name": name,
                "matched": _condition_matches(name, params, scenario)
                if isinstance(params, dict)
                else None,
            }
            for name, params in conditions.items()
        ]
        matches = (
            all(result["matched"] is True for result in condition_results)
            if all(result["matched"] is not None for result in condition_results)
            else None
        )
        rule_results.append(
            {
                "index": index,
                "priority": index + 1,
                "matches": matches,
                "conditions": condition_results,
                "command_names": list(commands),
            }
        )

    _check_overlaps(normalized_rules, warnings)

    complete = not errors and all(rule["matches"] is not None for rule in rule_results)
    matched_indexes: list[int] = []
    effective_commands: dict[str, Any] = {}
    if complete:
        matched_indexes = [
            rule["index"] for rule in rule_results if rule["matches"] is True
        ]
        if not settings.get("can_invoke_multiple_rules", False):
            matched_indexes = matched_indexes[:1]

        if matched_indexes:
            if settings.get("always_apply_defaults", False):
                effective_commands.update(deepcopy(defaults))
            for index in matched_indexes:
                effective_commands.update(deepcopy(raw_rules[index]["commands"]))
        else:
            effective_commands.update(deepcopy(defaults))

    return {
        "valid": not errors,
        "simulation_complete": complete,
        "errors": errors,
        "warnings": warnings,
        "rules": rule_results,
        "matched_rule_indexes": matched_indexes,
        "effective_commands": effective_commands,
    }
