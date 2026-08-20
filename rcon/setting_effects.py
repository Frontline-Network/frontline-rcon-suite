"""Truthful, permission-aware effect metadata for direct game-server settings.

The game server is still the authority for the effective value.  This module
does not guess protocol defaults, cache age, or which Auto Settings rule is
currently active when no simulation context is available.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)

UNKNOWN_VALUE = {"state": "unknown", "value": None}
SUPPORTED_GAMES = {"hll": "supported", "hllv": "supported"}


GENERAL_SETTING_EFFECTS: dict[str, dict[str, Any]] = {
    "team_switch_cooldown": {
        "getter": "get_team_switch_cooldown",
        "setter": "set_team_switch_cooldown",
        "value_parameter": "minutes",
        "unit": "minutes",
        "view_permission": "api.can_view_team_switch_cooldown",
        "change_permission": "api.can_change_team_switch_cooldown",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["team_switch_wait_changes"],
        "conflicts": ["auto_settings"],
    },
    "max_ping_autokick": {
        "getter": "get_max_ping_autokick",
        "setter": "set_max_ping_autokick",
        "value_parameter": "max_ms",
        "unit": "milliseconds",
        "view_permission": "api.can_view_max_ping_autokick",
        "change_permission": "api.can_change_max_ping_autokick",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["high_ping_players_may_be_kicked"],
        "conflicts": ["auto_settings"],
    },
    "queue_length": {
        "getter": "get_queue_length",
        "setter": "set_queue_length",
        "value_parameter": "value",
        "unit": "players",
        "view_permission": "api.can_view_queue_length",
        "change_permission": "api.can_change_queue_length",
        "recommended": {"state": "known", "value": 6},
        "side_effects": ["queue_capacity_changes"],
        "conflicts": ["auto_settings"],
    },
    "vip_slots_num": {
        "getter": "get_vip_slots_num",
        "setter": "set_vip_slots_num",
        "value_parameter": "value",
        "unit": "slots",
        "view_permission": "api.can_view_vip_slots",
        "change_permission": "api.can_change_vip_slots",
        "recommended": {"state": "known", "value": 2},
        "side_effects": ["reserved_capacity_changes"],
        "conflicts": ["auto_settings", "real_vip"],
    },
    "autobalance_enabled": {
        "getter": "get_autobalance_enabled",
        "setter": "set_autobalance_enabled",
        "value_parameter": "value",
        "unit": "boolean",
        "view_permission": "api.can_view_autobalance_enabled",
        "change_permission": "api.can_change_autobalance_enabled",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["native_autobalance_behavior_changes"],
        "conflicts": ["auto_settings", "frontline_autobalancer"],
    },
    "autobalance_threshold": {
        "getter": "get_autobalance_threshold",
        "setter": "set_autobalance_threshold",
        "value_parameter": "max_diff",
        "unit": "players",
        "view_permission": "api.can_view_autobalance_threshold",
        "change_permission": "api.can_change_autobalance_threshold",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["native_autobalance_threshold_changes"],
        "conflicts": ["auto_settings", "frontline_autobalancer"],
    },
    "idle_autokick_time": {
        "getter": "get_idle_autokick_time",
        "setter": "set_idle_autokick_time",
        "value_parameter": "minutes",
        "unit": "minutes",
        "view_permission": "api.can_view_idle_autokick_time",
        "change_permission": "api.can_change_idle_autokick_time",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["idle_players_may_be_kicked"],
        "conflicts": ["auto_settings"],
    },
    "votekick_enabled": {
        "getter": "get_votekick_enabled",
        "setter": "set_votekick_enabled",
        "value_parameter": "value",
        "unit": "boolean",
        "view_permission": "api.can_view_votekick_enabled",
        "change_permission": "api.can_change_votekick_enabled",
        "recommended": UNKNOWN_VALUE,
        "side_effects": ["player_votekick_availability_changes"],
        "conflicts": ["auto_settings", "auto_votekick"],
    },
    "votekick_thresholds": {
        "getter": "get_votekick_thresholds",
        "setter": "set_votekick_thresholds",
        "value_parameter": "threshold_pairs",
        "unit": "thresholds",
        "view_permission": "api.can_view_votekick_threshold",
        "change_permission": "api.can_change_votekick_threshold",
        "recommended": {
            "state": "known",
            "value": [[0, 1], [10, 5], [25, 12], [50, 20]],
        },
        "side_effects": ["required_votekick_votes_change"],
        "conflicts": ["auto_settings", "auto_votekick"],
        "restore": {
            "supported": True,
            "command": "reset_votekick_thresholds",
            "permission": "api.can_reset_votekick_threshold",
        },
    },
}


def _has_permission(user: Any, permission: str) -> bool:
    if bool(getattr(user, "is_superuser", False)):
        return True
    has_perm = getattr(user, "has_perm", None)
    return bool(callable(has_perm) and has_perm(permission))


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _audit_outcome(raw_result: Any) -> str:
    if not isinstance(raw_result, str):
        return "unknown"
    try:
        result = json.loads(raw_result)
    except (TypeError, ValueError):
        return "unknown"
    if not isinstance(result, dict) or "failed" not in result:
        return "unknown"
    if bool(result["failed"]) or result.get("error") not in (None, ""):
        return "failed"
    if result.get("result") is False:
        return "failed"
    return "succeeded"


def summarize_setting_audits(
    records: Iterable[Any], commands: Iterable[str]
) -> dict[str, dict[str, Any]]:
    """Return the newest attempt and newest successful change per command."""

    wanted = set(commands)
    summaries: dict[str, dict[str, Any]] = {}
    ordered = sorted(
        (record for record in records if getattr(record, "command", None) in wanted),
        key=lambda record: int(getattr(record, "id", 0) or 0),
        reverse=True,
    )
    for record in ordered:
        command = record.command
        outcome = _audit_outcome(getattr(record, "command_result", None))
        summary = summaries.setdefault(
            command,
            {
                "last_attempt": {
                    "audit_id": record.id,
                    "actor": record.username,
                    "at": _isoformat(record.creation_time),
                    "outcome": outcome,
                },
                "last_successful_change": None,
            },
        )
        if outcome == "succeeded" and summary["last_successful_change"] is None:
            summary["last_successful_change"] = {
                "audit_id": record.id,
                "actor": record.username,
                "at": _isoformat(record.creation_time),
            }
    return summaries


def analyze_auto_settings_management(
    config: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """List configured Auto Settings candidates without claiming a live match."""

    managed: dict[str, dict[str, Any]] = {
        key: {"managed": False, "candidates": []} for key in GENERAL_SETTING_EFFECTS
    }
    if not isinstance(config, Mapping):
        return managed

    sources: list[tuple[str, Mapping[str, Any]]] = []
    defaults = config.get("defaults")
    if isinstance(defaults, Mapping):
        sources.append(("defaults", defaults))
    rules = config.get("rules")
    if isinstance(rules, list):
        for index, rule in enumerate(rules):
            if isinstance(rule, Mapping) and isinstance(rule.get("commands"), Mapping):
                sources.append((f"rule:{index}", rule["commands"]))

    for setting_key, metadata in GENERAL_SETTING_EFFECTS.items():
        command = metadata["setter"]
        parameter = metadata["value_parameter"]
        for source, commands in sources:
            if command not in commands:
                continue
            raw_value = commands[command]
            value = (
                raw_value.get(parameter)
                if isinstance(raw_value, Mapping) and parameter in raw_value
                else None
            )
            managed[setting_key]["managed"] = True
            managed[setting_key]["candidates"].append(
                {
                    "source": source,
                    "value_state": "known" if value is not None else "unknown",
                    "value": deepcopy(value),
                }
            )
    return managed


def build_setting_effects_snapshot(
    *,
    rcon_api: Any,
    user: Any,
    server_number: int,
    game: str,
    auto_settings: Mapping[str, Any] | None = None,
    auto_settings_state: str = "permission_missing",
    audit_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    audit_state: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a safe setting-state matrix from live values and known metadata."""

    generated_at = generated_at or datetime.now(UTC)
    generated_at_iso = _isoformat(generated_at)
    normalized_game = game if game in SUPPORTED_GAMES else "unknown"
    automation = analyze_auto_settings_management(
        auto_settings if auto_settings_state == "available" else None
    )
    audit_summaries = audit_summaries or {}
    can_view_audit = _has_permission(user, "api.can_view_audit_logs")
    if audit_state is None:
        audit_state = "available" if can_view_audit else "permission_missing"

    settings: list[dict[str, Any]] = []
    visible_count = 0
    available_count = 0
    for setting_key, metadata in GENERAL_SETTING_EFFECTS.items():
        can_view = _has_permission(user, metadata["view_permission"])
        can_change = _has_permission(user, metadata["change_permission"])
        restore = deepcopy(
            metadata.get(
                "restore",
                {"supported": False, "command": None, "permission": None},
            )
        )
        restore["allowed"] = bool(
            can_view
            and restore["supported"]
            and restore["permission"]
            and _has_permission(user, restore["permission"])
        )
        if not can_view:
            change_blocked_reason = "missing_view_permission"
        elif not can_change:
            change_blocked_reason = "missing_change_permission"
        else:
            change_blocked_reason = None

        item: dict[str, Any] = {
            "key": setting_key,
            "unit": metadata["unit"],
            "visibility": "available" if can_view else "permission_missing",
            "required_view_permission": metadata["view_permission"],
            "change": {
                "allowed": can_view and can_change,
                "permission_granted": can_change,
                "required_permission": metadata["change_permission"],
                "command": metadata["setter"],
                "blocked_reason": change_blocked_reason,
            },
            "configured": deepcopy(UNKNOWN_VALUE),
            "effective": deepcopy(UNKNOWN_VALUE),
            "default": deepcopy(UNKNOWN_VALUE),
            "recommended": deepcopy(metadata["recommended"]),
            "activation": "immediate",
            "side_effects": list(metadata["side_effects"]),
            "conflicts": list(metadata["conflicts"]),
            "compatibility": {
                "current_game": normalized_game,
                "current_state": SUPPORTED_GAMES.get(normalized_game, "unknown"),
                "games": dict(SUPPORTED_GAMES),
            },
            "automation": {
                "state": auto_settings_state,
                **automation[setting_key],
            },
            "audit": {
                "state": audit_state if can_view_audit else "permission_missing",
                "required_permission": "api.can_view_audit_logs",
                "last_attempt": None,
                "last_successful_change": None,
            },
            "restore": restore,
            "next_action": None,
        }

        if can_view:
            visible_count += 1
            try:
                value = getattr(rcon_api, metadata["getter"])()
            except Exception:
                logger.exception(
                    "Unable to read setting effect value for %s", setting_key
                )
                item["configured"] = {"state": "unavailable", "value": None}
                item["effective"] = {
                    "state": "unavailable",
                    "value": None,
                    "source": "game_server_rcon",
                    "read_at": generated_at_iso,
                    "freshness": "unknown",
                }
                item["next_action"] = "check_game_server_connection"
            else:
                available_count += 1
                observed = {
                    "state": "observed",
                    "value": deepcopy(value),
                    "source": "game_server_rcon_or_cache",
                    "read_at": generated_at_iso,
                    "freshness": "unknown",
                }
                item["configured"] = deepcopy(observed)
                item["effective"] = observed
        else:
            item["configured"] = {"state": "permission_missing", "value": None}
            item["effective"] = {"state": "permission_missing", "value": None}
            item["next_action"] = "request_view_permission"

        if can_view_audit and audit_state == "available":
            summary = audit_summaries.get(metadata["setter"])
            if summary:
                item["audit"].update(deepcopy(summary))
            else:
                item["audit"]["state"] = "not_recorded"
        settings.append(item)

    if visible_count == 0:
        health = "unknown"
    elif available_count == 0:
        health = "unavailable"
    elif available_count < visible_count:
        health = "partial"
    else:
        health = "available"

    if visible_count == len(GENERAL_SETTING_EFFECTS):
        visibility = "full"
    elif visible_count:
        visibility = "partial"
    else:
        visibility = "none"

    return {
        "schema_version": 1,
        "generated_at": generated_at_iso,
        "server_number": server_number,
        "game": normalized_game,
        "health": health,
        "visibility": visibility,
        "settings": settings,
    }
