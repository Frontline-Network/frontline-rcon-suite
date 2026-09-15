"""Position-based combat-area checks for the seeding automod.

The grid calculation follows the RCONv2 approach used by
https://github.com/FlorianSW/hll-geofences and its go-hll-rcon dependency.
World coordinates are expressed in Unreal Engine centimetres.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any, Literal

import hllrcon
from hllrcon.data.maps import CardinalDirection

TeamName = Literal["allies", "axis"]
WorldPosition = tuple[float, float, float]

DEFAULT_WARFARE_GRID_SIZE_CM = 19_840.0
WARFARE_GRID_SIZE_CM_BY_MAP = {
    "carentan": 20_160.0,
    "elsenbornridge": 20_000.0,
    "junobeach": 20_000.0,
    "mortain": 20_000.0,
    "smolensk": 20_000.0,
    "tobruk": 20_000.0,
}
GRID_CELLS_PER_OBJECTIVE = 2
MAP_GRID_CELLS = 10

# Backport only the map-side data fix from hllrcon >= 2.0.0.3:
# https://github.com/timraay/hllrcon/commit/35d428a0686bf21e759e18a6f27a4b949528c40c
# Our pinned 2.0.0.0 mirrors these five HLL maps, causing own-HQ punishments.
# Explicit corrected values (not a blanket reversal) also remain correct after
# a future dependency upgrade. Do not mutate shared catalog objects or HLLV.
HLL_ALLIES_DIRECTION_CORRECTIONS = {
    "elsenbornridge": CardinalDirection.TOP_TO_BOTTOM,
    "kharkov": CardinalDirection.TOP_TO_BOTTOM,
    "kursk": CardinalDirection.TOP_TO_BOTTOM,
    "purpleheartlane": CardinalDirection.TOP_TO_BOTTOM,
    "stmariedumont": CardinalDirection.TOP_TO_BOTTOM,
}


def normalize_world_position(raw: Any) -> WorldPosition | None:
    """Return a numeric XYZ tuple, or ``None`` for an unusable payload."""
    if not isinstance(raw, Mapping):
        return None

    try:
        position = (float(raw["x"]), float(raw["y"]), float(raw["z"]))
    except (KeyError, TypeError, ValueError):
        return None

    return position if all(isfinite(coordinate) for coordinate in position) else None


def is_spawned(position: WorldPosition) -> bool:
    """Whether a position points at the game world instead of the spawn UI."""
    return any(coordinate != 0 for coordinate in position)


def _map_direction(map_id: str, team: TeamName) -> CardinalDirection | None:
    for map_catalog in (hllrcon.HLLMap, hllrcon.HLLVMap):
        try:
            map_ = map_catalog.by_id(map_id)
        except ValueError:
            continue

        allied_direction = map_.allies_direction
        if map_catalog is hllrcon.HLLMap:
            allied_direction = HLL_ALLIES_DIRECTION_CORRECTIONS.get(
                map_.id, allied_direction
            )
        return allied_direction if team == "allies" else allied_direction.get_opposite()

    return None


def is_outside_combat_area(
    position: WorldPosition,
    *,
    map_id: str,
    team: TeamName,
    max_caps: int,
) -> bool | None:
    """Check whether a player crossed into the next objective sector.

    ``None`` means the map is not known well enough for a safe positional
    decision, allowing the caller to use a less precise fallback signal.
    """
    direction = _map_direction(map_id, team)
    if direction is None:
        return None

    grid_size = WARFARE_GRID_SIZE_CM_BY_MAP.get(
        map_id.lower(), DEFAULT_WARFARE_GRID_SIZE_CM
    )
    allowed_grid_cells = max_caps * GRID_CELLS_PER_OBJECTIVE
    if not 0 < allowed_grid_cells < MAP_GRID_CELLS:
        return None

    if direction in (
        CardinalDirection.LEFT_TO_RIGHT,
        CardinalDirection.RIGHT_TO_LEFT,
    ):
        coordinate = position[0]
    else:
        coordinate = position[1]

    if direction in (
        CardinalDirection.LEFT_TO_RIGHT,
        CardinalDirection.TOP_TO_BOTTOM,
    ):
        boundary = (-MAP_GRID_CELLS / 2 + allowed_grid_cells) * grid_size
        return coordinate >= boundary

    boundary = (MAP_GRID_CELLS / 2 - allowed_grid_cells) * grid_size
    return coordinate < boundary
