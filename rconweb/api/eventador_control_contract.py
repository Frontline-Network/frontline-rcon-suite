"""Pure contract and game boundary for Eventador-controlled match steps."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from rcon.maps import Team
from rcon.utils import MapsHistory, get_server_number

SCHEMA_VERSION = 1
MAX_PLAYERS = 100
MAX_MESSAGE_CHARACTERS = 500
PREPARE_TTL_SECONDS = 300
EXECUTE_EARLY_TOLERANCE_SECONDS = 5
EXECUTE_LATE_TOLERANCE_SECONDS = 30

STEP_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
PLAYER_ID = re.compile(r"^[A-Za-z0-9:_-]{1,128}$")
MAP_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")

ACTION_REQUIREMENTS = {
    "observe": ("get_status", "get_map", "get_all_player_info"),
    "broadcast": ("get_status", "get_map", "get_all_player_info", "set_broadcast"),
    "message_players": (
        "get_status",
        "get_map",
        "get_all_player_info",
        "message_player",
    ),
    "set_map": ("get_status", "get_map", "get_all_player_info", "set_map"),
    "restart_round": ("get_status", "get_map", "get_all_player_info", "set_map"),
    "switch_players": (
        "get_status",
        "get_map",
        "get_all_player_info",
        "switch_player_now",
    ),
    "set_pause": ("get_status", "get_map", "get_all_player_info", "set_broadcast"),
}
MUTATING_ACTIONS = frozenset(ACTION_REQUIREMENTS) - {"observe"}


class ContractError(ValueError):
    """A caller-provided plan does not match the frozen v1 contract."""


class KnownActionFailure(RuntimeError):
    """The game server explicitly rejected an action without an ambiguous result."""

    def __init__(self, result: dict[str, Any]):
        super().__init__("the game server rejected the action")
        self.result = result


class ActionOutcomeUnknown(RuntimeError):
    """An action raised after dispatch, so replay would be unsafe."""

    def __init__(self, result: dict[str, Any]):
        super().__init__("the game action outcome is unknown")
        self.result = result


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractError(f"{label} must contain exactly {sorted(keys)}")
    return value


def _integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{label} must be an integer")
    if not minimum <= value <= maximum:
        raise ContractError(f"{label} is outside the allowed range")
    return value


def _text(
    value: Any,
    maximum: int,
    label: str,
    pattern: re.Pattern[str] | None = None,
) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ContractError(f"{label} must be a non-empty bounded string")
    if pattern and not pattern.fullmatch(value):
        raise ContractError(f"{label} has an invalid format")
    return value


def _uuid4(value: Any, label: str) -> str:
    text = _text(value, 36, label)
    try:
        parsed = uuid.UUID(text)
    except ValueError as exc:
        raise ContractError(f"{label} must be a UUIDv4") from exc
    if parsed.version != 4 or str(parsed) != text.lower():
        raise ContractError(f"{label} must be a canonical UUIDv4")
    return text.lower()


def parse_timestamp(value: Any, label: str) -> datetime:
    text = _text(value, 64, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def schedule_conflict(now: datetime, execute_at: datetime) -> str | None:
    """Return a stable conflict code when a step is outside the v1 window."""

    delta = (execute_at - now).total_seconds()
    if delta < -EXECUTE_LATE_TOLERANCE_SECONDS:
        return "execution_window_expired"
    if delta > PREPARE_TTL_SECONDS:
        return "execution_window_too_far"
    return None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_game(value: Any) -> str:
    raw = str(getattr(value, "value", value)).strip().lower()
    if raw == "hll":
        return "hll"
    if raw in {"hllv", "hll_vietnam", "hell-let-loose-vietnam"}:
        return "hllv"
    raise ContractError("the active game profile is unsupported")


def validate_plan(value: Any) -> dict[str, Any]:
    plan = _exact(
        value,
        {
            "schema_version",
            "event_id",
            "event_revision",
            "workflow_revision",
            "step_id",
            "idempotency_key",
            "execute_at",
            "target",
            "action",
            "reason",
            "arguments",
            "expected",
        },
        "plan",
    )
    if plan["schema_version"] != SCHEMA_VERSION:
        raise ContractError("schema_version must be 1")
    _uuid4(plan["event_id"], "event_id")
    _integer(plan["event_revision"], 1, 2**31 - 1, "event_revision")
    _integer(plan["workflow_revision"], 1, 2**31 - 1, "workflow_revision")
    _text(plan["step_id"], 64, "step_id", STEP_ID)
    _uuid4(plan["idempotency_key"], "idempotency_key")
    parse_timestamp(plan["execute_at"], "execute_at")
    target = _exact(plan["target"], {"server_number", "game"}, "target")
    _integer(target["server_number"], 1, 65_535, "target.server_number")
    if target["game"] not in {"hll", "hllv"}:
        raise ContractError("target.game must be hll or hllv")
    action = plan["action"]
    if action not in ACTION_REQUIREMENTS:
        raise ContractError("action is not allowed")
    _text(plan["reason"], MAX_MESSAGE_CHARACTERS, "reason")
    _validate_arguments(action, plan["arguments"])
    expected = _exact(
        plan["expected"],
        {"map", "round_id", "roster_hash", "state_observed_at", "previous_step_id"},
        "expected",
    )
    expected_map = _text(expected["map"], 128, "expected.map", MAP_ID)
    _text(expected["round_id"], 64, "expected.round_id", SHA256)
    _text(expected["roster_hash"], 64, "expected.roster_hash", SHA256)
    parse_timestamp(expected["state_observed_at"], "expected.state_observed_at")
    if expected["previous_step_id"] is not None:
        _text(expected["previous_step_id"], 64, "expected.previous_step_id", STEP_ID)
    if action == "restart_round" and plan["arguments"]["map"] != expected_map:
        raise ContractError("restart_round map must match expected.map")
    return plan


def _validate_arguments(action: str, value: Any) -> None:
    if action == "observe":
        _exact(value, set(), "arguments")
        return
    if action == "broadcast":
        args = _exact(value, {"message"}, "arguments")
        _text(args["message"], MAX_MESSAGE_CHARACTERS, "arguments.message")
        return
    if action == "message_players":
        args = _exact(value, {"message", "player_ids"}, "arguments")
        _text(args["message"], MAX_MESSAGE_CHARACTERS, "arguments.message")
        players = args["player_ids"]
        if not isinstance(players, list) or not 1 <= len(players) <= MAX_PLAYERS:
            raise ContractError("arguments.player_ids must contain 1 to 100 players")
        normalized = [
            _text(item, 128, "arguments.player_ids item", PLAYER_ID) for item in players
        ]
        if len(set(normalized)) != len(normalized):
            raise ContractError("arguments.player_ids contains duplicates")
        return
    if action in {"set_map", "restart_round"}:
        args = _exact(value, {"map"}, "arguments")
        _text(args["map"], 128, "arguments.map", MAP_ID)
        return
    if action == "set_pause":
        args = _exact(value, {"status", "message"}, "arguments")
        if args["status"] not in {"paused", "resumed"}:
            raise ContractError("arguments.status must be paused or resumed")
        _text(args["message"], MAX_MESSAGE_CHARACTERS, "arguments.message")
        return
    args = _exact(value, {"players"}, "arguments")
    players = args["players"]
    if not isinstance(players, list) or not 1 <= len(players) <= MAX_PLAYERS:
        raise ContractError("arguments.players must contain 1 to 100 players")
    seen: set[str] = set()
    for item in players:
        player = _exact(item, {"player_id", "target_team"}, "player")
        player_id = _text(player["player_id"], 128, "player.player_id", PLAYER_ID)
        if player["target_team"] not in {"allies", "axis"}:
            raise ContractError("player.target_team must be allies or axis")
        if player_id in seen:
            raise ContractError("arguments.players contains duplicates")
        seen.add(player_id)


def build_capabilities(rcon_api: Any, execution_enabled: bool) -> dict[str, Any]:
    game = normalize_game(rcon_api.game_profile.game)
    actions = {}
    for action, requirements in ACTION_REQUIREMENTS.items():
        actions[action] = {
            "available": all(
                callable(getattr(rcon_api, name, None)) for name in requirements
            ),
            "mutates_game": action in MUTATING_ACTIONS,
            "required_legacy_commands": list(requirements),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "game": game,
        "execution_enabled": execution_enabled,
        "actions": actions,
        "limits": {
            "max_players_per_step": MAX_PLAYERS,
            "max_message_characters": MAX_MESSAGE_CHARACTERS,
            "prepare_ttl_seconds": PREPARE_TTL_SECONDS,
        },
        "interface": {
            "version": "v1",
            "capabilities_path": "/api/eventador/v1/capabilities",
            "state_path": "/api/eventador/v1/state",
            "prepare_path": "/api/eventador/v1/steps/prepare",
            "execute_path_template": "/api/eventador/v1/steps/{preparation_id}/execute",
            "result_path_template": "/api/eventador/v1/results/{idempotency_key}",
            "authentication": "dedicated_api_key_and_permission",
        },
    }


def build_state(rcon_api: Any, captured_at: datetime | None = None) -> dict[str, Any]:
    now = (captured_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    status = rcon_api.get_status()
    game = normalize_game(status.get("game", rcon_api.game_profile.game))
    server_number = int(status.get("server_number", get_server_number()))
    if game != normalize_game(rcon_api.game_profile.game):
        raise ContractError("the live status does not match the active game profile")
    if server_number != int(get_server_number()):
        raise ContractError("the live status does not match the configured server")
    map_id = str(rcon_api.get_map())
    _text(map_id, 128, "map", MAP_ID)
    if status.get("map") is not None and str(status["map"]) != map_id:
        raise ContractError("the live status returned inconsistent maps")
    raw_players = rcon_api.get_all_player_info()
    players: dict[str, dict[str, str | None]] = {}
    for raw in raw_players:
        player_id = _text(raw.get("iD"), 128, "player_id", PLAYER_ID)
        if player_id in players:
            raise ContractError("the live roster contains duplicate player ids")
        team = rcon_api.game_profile.team_for_id(raw.get("team"))
        players[player_id] = {
            "player_id": player_id,
            "team": team.value if team in {Team.ALLIES, Team.AXIS} else None,
        }
    if len(players) > MAX_PLAYERS:
        raise ContractError("the live roster exceeds the Eventador limit")
    history = MapsHistory().get_current_map() or {}
    start = history.get("start")
    recorded_map = history.get("name")
    if (
        not isinstance(start, (int, float))
        or isinstance(start, bool)
        or start <= 0
        or recorded_map != map_id
        or history.get("end") is not None
    ):
        raise ContractError("the current round identity is unavailable")
    stable_start = int(start)
    round_id = digest(
        {
            "server_number": server_number,
            "game": game,
            "map": map_id,
            "started_at": stable_start,
        }
    )
    ordered_players = {key: players[key] for key in sorted(players)}
    return {
        "captured_at": now.isoformat().replace("+00:00", "Z"),
        "map": map_id,
        "round_id": round_id,
        "roster_hash": digest(ordered_players),
        "players": ordered_players,
        "status": {
            "server_number": server_number,
            "game": game,
            "current_players": len(ordered_players),
        },
    }


def state_matches_plan(state: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    expected = plan["expected"]
    return (
        state["map"] == expected["map"]
        and state["round_id"] == expected["round_id"]
        and state["roster_hash"] == expected["roster_hash"]
        and state["status"]["server_number"] == plan["target"]["server_number"]
        and state["status"]["game"] == plan["target"]["game"]
    )


def runtime_scope_matches(
    rcon_api: Any, state: Mapping[str, Any], plan: Mapping[str, Any]
) -> bool:
    """Validate action-specific targets without performing a mutation."""

    action = plan["action"]
    arguments = plan["arguments"]
    if not all(
        callable(getattr(rcon_api, name, None)) for name in ACTION_REQUIREMENTS[action]
    ):
        return False
    if action in {"set_map", "restart_round"}:
        try:
            parsed = rcon_api.game_profile.parse_layer(arguments["map"])
        except (KeyError, TypeError, ValueError):
            return False
        parsed_map = getattr(parsed, "map", None)
        parsed_mode = getattr(parsed, "game_mode", None)
        if (
            str(parsed) != arguments["map"]
            or getattr(parsed_map, "id", "unknown").lower() == "unknown"
            or str(getattr(parsed_mode, "value", parsed_mode)).lower() == "unknown"
        ):
            return False
    if action == "message_players":
        return all(
            player_id in state["players"] for player_id in arguments["player_ids"]
        )
    if action == "switch_players":
        for player in arguments["players"]:
            current = state["players"].get(player["player_id"])
            if not current or current.get("team") not in {"allies", "axis"}:
                return False
            if current["team"] == player["target_team"]:
                return False
    return True


def _remaining_targets(items: list[Any], offset: int) -> list[dict[str, Any]]:
    result = []
    for item in items[offset:]:
        player_id = item if isinstance(item, str) else item["player_id"]
        result.append({"player_id": player_id, "status": "not_attempted"})
    return result


def execute_game_action(rcon_api: Any, plan: Mapping[str, Any]) -> dict[str, Any]:
    action = plan["action"]
    arguments = plan["arguments"]
    if action == "observe":
        return {
            "action": action,
            "targets": [{"kind": "server", "status": "succeeded"}],
        }
    if action == "broadcast":
        result = {
            "action": action,
            "targets": [{"kind": "server", "status": "unknown"}],
        }
        try:
            rcon_api.set_broadcast(arguments["message"])
        except Exception as exc:
            raise ActionOutcomeUnknown(result) from exc
        result["targets"][0]["status"] = "succeeded"
        return result
    if action == "message_players":
        players = arguments["player_ids"]
        targets = []
        for offset, player_id in enumerate(players):
            target = {"player_id": player_id, "status": "unknown"}
            targets.append(target)
            try:
                accepted = rcon_api.message_player(
                    player_id, message=arguments["message"]
                )
            except Exception as exc:
                targets.extend(_remaining_targets(players, offset + 1))
                raise ActionOutcomeUnknown(
                    {"action": action, "targets": targets}
                ) from exc
            if not accepted:
                target["status"] = "failed"
                targets.extend(_remaining_targets(players, offset + 1))
                raise KnownActionFailure({"action": action, "targets": targets})
            target["status"] = "succeeded"
        return {"action": action, "targets": targets}
    if action in {"set_map", "restart_round"}:
        result = {
            "action": action,
            "targets": [
                {"kind": "server", "map": arguments["map"], "status": "unknown"}
            ],
        }
        try:
            rcon_api.set_map(arguments["map"])
        except Exception as exc:
            raise ActionOutcomeUnknown(result) from exc
        result["targets"][0]["status"] = "succeeded"
        return result
    if action == "switch_players":
        players = arguments["players"]
        targets = []
        for offset, player in enumerate(players):
            target = {
                "player_id": player["player_id"],
                "target_team": player["target_team"],
                "status": "unknown",
            }
            targets.append(target)
            try:
                accepted = rcon_api.switch_player_now(player["player_id"])
            except Exception as exc:
                targets.extend(_remaining_targets(players, offset + 1))
                raise ActionOutcomeUnknown(
                    {"action": action, "targets": targets}
                ) from exc
            if not accepted:
                target["status"] = "failed"
                targets.extend(_remaining_targets(players, offset + 1))
                raise KnownActionFailure({"action": action, "targets": targets})
            target["status"] = "succeeded"
        return {"action": action, "targets": targets}
    if action == "set_pause":
        result = {
            "action": action,
            "targets": [
                {
                    "kind": "server",
                    "pause_status": arguments["status"],
                    "status": "unknown",
                }
            ],
        }
        try:
            rcon_api.set_broadcast(arguments["message"])
        except Exception as exc:
            raise ActionOutcomeUnknown(result) from exc
        result["targets"][0]["status"] = "succeeded"
        return result
    raise ContractError("action is not allowed")
