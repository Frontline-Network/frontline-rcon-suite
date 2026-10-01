"""Versioned HLL Vietnam layer data retained independently from ``hllrcon``.

``hllrcon`` correctly describes the live protocol, but its generated data is
allowed to drop obsolete IDs.  CRCON also reads historical rounds, where a
removed ID must still render with its original map, mode and factions.  Keep
the initial HLLV catalogue here as a deliberately small, declarative snapshot
and extend it whenever the game changes an identifier.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from logging import getLogger

from rcon.maps import Environment, Faction, GameMode, Layer, Map, Orientation, Team

logger = getLogger(__name__)

# Bump this whenever a new game build changes or removes an HLLV identifier.
HLLV_LEGACY_CATALOG_VERSION = "2026.09.27.1"


@dataclass(frozen=True)
class _MapDefinition:
    layer_prefix: str
    map_id: str
    name: str
    tag: str
    shortname: str
    orientation: Orientation


_MAP_DEFINITIONS = (
    _MapDefinition("wdeve", "WDEV_E", "Cam Ranh Port", "CAM", "Cam Ranh", Orientation.HORIZONTAL),
    _MapDefinition("wdevd", "WDEV_D", "Đăk Tô Airfield", "DAK", "Đăk Tô", Orientation.HORIZONTAL),
    _MapDefinition("wdevc", "WDEV_C", "Huế Outskirts", "HUE", "Huế", Orientation.VERTICAL),
    _MapDefinition("wdevb", "WDEV_B", "Quảng Ngãi", "QUA", "Quảng Ngãi", Orientation.HORIZONTAL),
    _MapDefinition("wdevf", "WDEV_F", "Thanh Hòa Bridge", "THA", "Thanh Hoa", Orientation.VERTICAL),
    _MapDefinition("wdeva", "WDEV_A", "Vạn Tường", "VAN", "Vạn Tường", Orientation.HORIZONTAL),
)


def _map(definition: _MapDefinition) -> Map:
    return Map(
        id=definition.map_id,
        name=definition.name.upper(),
        tag=definition.tag,
        pretty_name=definition.name,
        shortname=definition.shortname,
        allies=Faction(name="us", team=Team.ALLIES),
        axis=Faction(name="nva", team=Team.AXIS),
        orientation=definition.orientation,
    )


HLLV_LEGACY_MAPS: dict[str, Map] = {}
for _definition in _MAP_DEFINITIONS:
    _legacy_map = _map(_definition)
    # Current and historic hllrcon builds have used both variants.
    HLLV_LEGACY_MAPS[_definition.layer_prefix] = _legacy_map
    HLLV_LEGACY_MAPS[_legacy_map.id.lower()] = _legacy_map


def _layer(map_id: str, mode: GameMode, attackers: Team | None = None) -> Layer:
    attacker_suffix = (
        "nva" if attackers is Team.AXIS else "us" if attackers is Team.ALLIES else ""
    )
    return Layer(
        id=f"{map_id}_{mode.value}{attacker_suffix}_day",
        map=HLLV_LEGACY_MAPS[map_id],
        game_mode=mode,
        attackers=attackers,
        environment=Environment.DAY,
    )


HLLV_LEGACY_LAYERS: dict[str, Layer] = {}
for _definition in _MAP_DEFINITIONS:
    for _mode in (GameMode.WARFARE, GameMode.DOMINATION, GameMode.CONQUEST):
        _legacy_layer = _layer(_definition.layer_prefix, _mode)
        HLLV_LEGACY_LAYERS[_legacy_layer.id] = _legacy_layer
    for _attacker in (Team.ALLIES, Team.AXIS):
        _legacy_layer = _layer(
            _definition.layer_prefix, GameMode.OFFENSIVE, _attacker
        )
        HLLV_LEGACY_LAYERS[_legacy_layer.id] = _legacy_layer


def _human_map_aliases(definition: _MapDefinition) -> tuple[str, ...]:
    normalized = (
        definition.name.lower()
        .replace("đ", "d")
        .replace("ế", "e")
        .replace("ả", "a")
        .replace("ạ", "a")
        .replace("ò", "o")
        .replace(" ", "_")
    )
    # Keep the original aliases for compatibility, but also fully normalize
    # Vietnamese diacritics. Partial replacements missed e.g. van_tuong and
    # dak_to_airfield, so readable historical IDs resolved as unknown maps.
    ascii_name = unicodedata.normalize("NFKD", definition.name.lower().replace("đ", "d"))
    ascii_name = "".join(char for char in ascii_name if not unicodedata.combining(char))
    ascii_name = ascii_name.replace(" ", "_")
    return tuple(dict.fromkeys((definition.layer_prefix, normalized, ascii_name)))


# Aliases cover IDs observed before the explicit ``_day`` suffix as well as
# readable IDs used by early HLLV integrations.  Values always point at a
# canonical, currently executable layer ID.
HLLV_LEGACY_LAYER_ALIASES: dict[str, str] = {}
for _definition in _MAP_DEFINITIONS:
    for _canonical_id in tuple(HLLV_LEGACY_LAYERS):
        if not _canonical_id.startswith(f"{_definition.layer_prefix}_"):
            continue
        _without_day = _canonical_id.removesuffix("_day")
        HLLV_LEGACY_LAYER_ALIASES[_without_day] = _canonical_id
        for _map_alias in _human_map_aliases(_definition):
            HLLV_LEGACY_LAYER_ALIASES[
                _canonical_id.replace(_definition.layer_prefix, _map_alias, 1)
            ] = _canonical_id
            HLLV_LEGACY_LAYER_ALIASES[
                _without_day.replace(_definition.layer_prefix, _map_alias, 1)
            ] = _canonical_id

for _alias, _canonical_id in tuple(HLLV_LEGACY_LAYER_ALIASES.items()):
    HLLV_LEGACY_LAYER_ALIASES[_alias.replace("offensivenva", "offensive_nva")] = (
        _canonical_id
    )
    HLLV_LEGACY_LAYER_ALIASES[_alias.replace("offensiveus", "offensive_us")] = (
        _canonical_id
    )


@lru_cache(maxsize=128)
def report_unknown_hllv_layer(layer_id: str) -> None:
    """Emit one bounded, non-sensitive telemetry event per unknown layer ID."""
    logger.warning(
        "Unknown HLLV layer id '%s' encountered (legacy catalog %s)",
        layer_id,
        HLLV_LEGACY_CATALOG_VERSION,
    )
