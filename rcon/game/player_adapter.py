"""Validated, game-neutral player data at the RCON boundary.

The two games expose the same *concept* of a player, but HLLV's V2 protocol
uses a different documented field spelling in a few places (for example
``Id``, ``SteamId`` and ``Combat``).  Everything above this boundary consumes
``CanonicalPlayerInfo`` so report, moderation and UI code never needs to make
that distinction.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from rcon.types import CanonicalPlayerInfo, ScoreDataType, StatsDataType, WorldPositionType


class PlayerResponseAdapterError(ValueError):
    """A response cannot safely be associated with a player."""


class PlayerInfoAdapter(Protocol):
    """Convert one game protocol's raw player payload into the shared DTO."""

    def adapt(self, raw: Mapping[str, Any]) -> CanonicalPlayerInfo: ...

    def adapt_for_squad_check(self, raw: Mapping[str, Any]) -> CanonicalPlayerInfo: ...


class BasePlayerInfoAdapter:
    """Shared defensive normalization used by the per-game protocol adapters."""

    player_id_keys: tuple[str, ...] = ("iD", "playerId", "PlayerId", "id", "Id")
    eos_id_keys: tuple[str, ...] = ("eosId", "eosID", "eos_id")

    @staticmethod
    def _lookup(raw: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
        # The V2 documentation and actual packets have historically differed
        # only by casing.  Treat protocol keys case-insensitively at this one
        # boundary instead of leaking the ambiguity to feature code.
        for key in keys:
            if key in raw:
                return raw[key]

        by_lower_key = {str(key).lower(): value for key, value in raw.items()}
        for key in keys:
            if key.lower() in by_lower_key:
                return by_lower_key[key.lower()]
        return default

    @classmethod
    def _text(
        cls, raw: Mapping[str, Any], *keys: str, default: str = ""
    ) -> str:
        value = cls._lookup(raw, *keys, default=default)
        return default if value is None else str(value)

    @classmethod
    def _integer(cls, raw: Mapping[str, Any], *keys: str, default: int = 0) -> int:
        value = cls._lookup(raw, *keys, default=default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _number(cls, raw: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
        value = cls._lookup(raw, *keys, default=default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _mapping(cls, raw: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
        value = cls._lookup(raw, *keys, default={})
        return value if isinstance(value, Mapping) else {}

    def adapt_for_squad_check(self, raw: Mapping[str, Any]) -> CanonicalPlayerInfo:
        """A missing role or faction cannot safely default to a valid game ID."""
        player = self.adapt(raw)
        for field in ("team", "role"):
            value = self._lookup(raw, field)
            if type(value) is not int and not (
                isinstance(value, str) and value.removeprefix("-").isdecimal()
            ):
                raise PlayerResponseAdapterError(f"Player response has invalid {field}")
        if not isinstance(self._lookup(raw, "platoon"), str):
            raise PlayerResponseAdapterError("Player response has no platoon information")
        return player

    def adapt(self, raw: Mapping[str, Any]) -> CanonicalPlayerInfo:
        if not isinstance(raw, Mapping):
            raise PlayerResponseAdapterError("Player response is not an object")

        player_id = self._text(raw, *self.player_id_keys).strip()
        name = self._text(raw, "name", "Name").strip()
        if not player_id or not name:
            raise PlayerResponseAdapterError("Player response has no stable id or name")

        score_raw = self._mapping(raw, "scoreData", "ScoreData")
        stats_raw = self._mapping(raw, "stats", "Stats")
        position_raw = self._mapping(raw, "worldPosition", "WorldPosition")

        score_data: ScoreDataType = {
            "cOMBAT": self._integer(score_raw, "cOMBAT", "combat", "Combat"),
            "offense": self._integer(score_raw, "offense", "Offense"),
            "defense": self._integer(score_raw, "defense", "Defense"),
            "support": self._integer(score_raw, "support", "Support"),
        }
        stats: StatsDataType = {
            "teamKills": self._integer(stats_raw, "teamKills", "TeamKills"),
            "vehicleKills": self._integer(stats_raw, "vehicleKills", "VehicleKills"),
            "vehiclesDestroyed": self._integer(
                stats_raw, "vehiclesDestroyed", "VehiclesDestroyed"
            ),
            "infantryKills": self._integer(stats_raw, "infantryKills", "InfantryKills"),
            "deaths": self._integer(stats_raw, "deaths", "Deaths"),
        }
        world_position: WorldPositionType = {
            "x": self._number(position_raw, "x", "X"),
            "y": self._number(position_raw, "y", "Y"),
            "z": self._number(position_raw, "z", "Z"),
        }

        return {
            "iD": player_id,
            "team": self._integer(raw, "team", "Team"),
            "role": self._integer(raw, "role", "Role"),
            "level": self._integer(raw, "level", "Level"),
            "loadout": self._text(raw, "loadout", "Loadout"),
            "name": name,
            "platoon": self._text(raw, "platoon", "Platoon"),
            "platoonIndex": self._integer(raw, "platoonIndex", "PlatoonIndex"),
            "scoreData": score_data,
            "stats": stats,
            "platform": self._text(raw, "platform", "Platform"),
            "clanTag": self._text(raw, "clanTag", "ClanTag"),
            "eosId": self._text(raw, *self.eos_id_keys),
            "steamId": self._text(raw, "steamId", "SteamId", "steam_id") or None,
            "worldPosition": world_position,
        }
