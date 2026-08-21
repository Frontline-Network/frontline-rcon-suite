from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rcon.maps import GameMode, Layer, Map, Team
from rcon.types import GameEnum
from rcon.weapons import WeaponType

if TYPE_CHECKING:
    from rcon.game.player_adapter import PlayerInfoAdapter


@dataclass(frozen=True)
class SectorLayoutCapabilities:
    """Protocol operations available for selecting a five-sector layout.

    ``remove`` is deliberately separate from ``set``.  Neither supported game
    currently documents a command that clears a sector layout independently,
    so clients must not present a destructive reset action as if it existed.
    """

    read: bool = False
    set: bool = False
    remove: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {"read": self.read, "set": self.set, "remove": self.remove}


@dataclass(frozen=True)
class GameProfile:
    """Game-specific reference data and parsing behind a stable interface."""

    game: GameEnum
    maps: Mapping[str, Map]
    layers: Mapping[str, Layer]
    layer_parser: Callable[[str | Layer], Layer]
    roles: frozenset[str] = field(default_factory=frozenset)
    role_labels: Mapping[str, str] = field(default_factory=dict)
    weapons: Mapping[str, WeaponType] = field(default_factory=dict)
    weapon_sides: Mapping[str, Team] = field(default_factory=dict)
    supported_game_modes: frozenset[GameMode] = field(default_factory=frozenset)
    match_timer_modes: frozenset[GameMode] = field(default_factory=frozenset)
    warmup_timer_modes: frozenset[GameMode] = field(default_factory=frozenset)
    sector_layout: SectorLayoutCapabilities = field(
        default_factory=SectorLayoutCapabilities
    )
    game_mode_aliases: Mapping[str, GameMode] = field(default_factory=dict)
    player_adapter: "PlayerInfoAdapter | None" = None
    # Persisted unit history uses stable CRCON side IDs, not faction IDs. Both
    # games use 1/2 for Allies/Axis even though their live faction IDs differ.
    team_ids: Mapping[Team, int] = field(default_factory=dict)

    def parse_layer(self, layer_name: str | Layer) -> Layer:
        return self.layer_parser(layer_name)

    def parse_layer_or_unknown(self, layer_name: str | Layer) -> Layer:
        try:
            return self.parse_layer(layer_name)
        except (KeyError, TypeError, ValueError):
            return self.layers["unknown"]

    def parse_game_mode(self, game_mode: str | GameMode) -> GameMode:
        if isinstance(game_mode, GameMode):
            mode = game_mode
        else:
            normalized = game_mode.strip().lower()
            mode = self.game_mode_aliases.get(normalized, normalized)
            if not isinstance(mode, GameMode):
                mode = GameMode(mode)
        if mode not in self.supported_game_modes:
            raise ValueError(
                f"Game mode {mode.value!r} is not supported by the '{self.game.value}' game profile"
            )
        return mode

    def team_id_for(self, team: Team | str | None) -> int | None:
        """Return the persisted side ID for a logical CRCON team."""
        try:
            side = team if isinstance(team, Team) else Team(team or Team.UNKNOWN)
        except ValueError:
            return None
        return self.team_ids.get(side)

    def team_for_id(self, team_id: object) -> Team | None:
        """Resolve a persisted side ID without assuming a game-specific enum."""
        try:
            normalized = int(team_id)
        except (TypeError, ValueError):
            return None
        return next(
            (team for team, value in self.team_ids.items() if value == normalized),
            None,
        )
