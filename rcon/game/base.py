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
    game_mode_aliases: Mapping[str, GameMode] = field(default_factory=dict)
    player_adapter: "PlayerInfoAdapter | None" = None

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
