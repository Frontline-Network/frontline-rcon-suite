from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rcon.utils import MapsHistory, get_squad_leader_roles, get_team_labels

from .models import BalanceSnapshot, PlayerSnapshot
from .store import AutobalancerStore


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _map_name(game_state: dict[str, Any]) -> str:
    current = game_state.get("current_map") or {}
    if isinstance(current, str):
        return current
    return str(
        current.get("id")
        or current.get("name")
        or current.get("pretty_name")
        or "unknown"
    )


def _current_round(map_name: str, now: datetime) -> tuple[str, int, bool]:
    try:
        map_info = MapsHistory(max_len=1)[0]
        started_at = float(map_info.get("start") or 0)
        recorded_name = str(map_info.get("name") or map_name)
    except (IndexError, TypeError, ValueError, ConnectionError):
        return f"unknown:{map_name}", 0, False
    stable = bool(started_at and (recorded_name == map_name or map_name == "unknown"))
    elapsed = max(0, int(now.timestamp() - started_at)) if started_at else 0
    return f"{int(started_at)}:{recorded_name}", elapsed, stable


def build_snapshot(
    rcon,
    store: AutobalancerStore,
    now: datetime | None = None,
) -> BalanceSnapshot:
    now = now or datetime.now(timezone.utc)
    game_state = rcon.get_gamestate()
    team_view = rcon.get_team_view()
    game = rcon.game_profile.game
    leader_roles = get_squad_leader_roles(game)
    map_name = _map_name(game_state)
    round_id, elapsed, stable_map = _current_round(map_name, now)
    raw_players: list[tuple[str, dict[str, Any], str | None, dict[str, Any]]] = []

    for team in ("allies", "axis"):
        team_data = team_view.get(team) or {}
        commander = team_data.get("commander")
        if commander:
            raw_players.append(
                (
                    team,
                    commander,
                    "command",
                    {"type": "commander", "players": [commander]},
                )
            )
        for squad_name, squad in (team_data.get("squads") or {}).items():
            for player in squad.get("players") or []:
                raw_players.append((team, player, squad_name, squad))

    memberships = {
        str(player.get("player_id")): (
            f"{team}:{player.get('unit_id') or squad_name}" if squad_name else None
        )
        for team, player, squad_name, _ in raw_players
        if player.get("player_id")
    }
    squad_seconds = store.track_squad_memberships(round_id, memberships, now)
    players: list[PlayerSnapshot] = []
    for team, player, squad_name, squad in raw_players:
        profile = player.get("profile") or {}
        role = str(player.get("role") or "")
        players.append(
            PlayerSnapshot(
                player_id=str(player.get("player_id") or ""),
                name=str(player.get("name") or "Unknown"),
                team=team,
                role=role,
                level=(
                    _as_int(player.get("level"))
                    if player.get("level") is not None
                    else None
                ),
                unit_id=player.get("unit_id"),
                unit_name=player.get("unit_name") or squad_name,
                unit_type=squad.get("type"),
                unit_size=len(squad.get("players") or []),
                is_leader=role in leader_roles,
                connected_seconds=_as_int(profile.get("current_playtime_seconds")),
                squad_seconds=squad_seconds.get(str(player.get("player_id")), 0),
                map_playtime_seconds=_as_int(player.get("map_playtime_seconds")),
                kills=_as_int(player.get("kills")),
                combat=_as_int(player.get("combat")),
                offense=_as_int(player.get("offense")),
                defense=_as_int(player.get("defense")),
                support=_as_int(player.get("support")),
                deaths=_as_int(player.get("deaths")),
                teamkills=_as_int(player.get("teamkills")),
            )
        )

    allies_view_count = _as_int((team_view.get("allies") or {}).get("count"))
    axis_view_count = _as_int((team_view.get("axis") or {}).get("count"))
    allies_count = _as_int(game_state.get("num_allied_players"))
    axis_count = _as_int(game_state.get("num_axis_players"))
    try:
        remaining = int(game_state["time_remaining"].total_seconds())
    except (AttributeError, KeyError, TypeError):
        remaining = 0
    try:
        native_enabled = bool(rcon.get_autobalance_enabled())
        native_threshold = int(rcon.get_autobalance_threshold())
    except Exception:
        native_enabled = None
        native_threshold = None
    return BalanceSnapshot(
        round_id=round_id,
        captured_at=now,
        map_name=map_name,
        map_elapsed_seconds=elapsed,
        time_remaining_seconds=remaining,
        allies_count=allies_count,
        axis_count=axis_count,
        players=players,
        game=game.value,
        fail_count=_as_int(team_view.get("fail_count")),
        counts_match=(
            allies_view_count == allies_count
            and axis_view_count == axis_count
            and len(players) == allies_count + axis_count
        ),
        stable_map=stable_map,
        native_autobalance_enabled=native_enabled,
        native_autobalance_threshold=native_threshold,
        team_labels=get_team_labels(
            game,
            game_state.get("allied_faction_id", game_state.get("allied_faction")),
            game_state.get("axis_faction_id", game_state.get("axis_faction")),
        ),
    )
