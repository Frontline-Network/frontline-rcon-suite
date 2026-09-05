"""Display-only projections, separate from independently verified calibration.

Quang Ngai and Thanh Hoa have paired stationary WorldPosition / in-game-grid
observations suggesting a -100000..100000 XY display frame. The operator has
explicitly requested this provisional display for all six extracted HLLV maps,
confirming alignment of the tactical images with the game maps. Applying the
same world frame to the other four maps remains an unvalidated assumption.
This is NOT decoded map metadata, a measured metre scale, or a <=10 m claim.

The operator also enabled the shipped HLL tactical images. Their display uses
the same centred XY frame as an explicit display assumption, NOT as a verified
calibration. Keep this allowlist separate from HLLV and from metric evidence;
an operator's measured per-map calibration always takes precedence.
"""
from copy import deepcopy


DISPLAY_PREVIEWS = {
    "wdev_a": "Van Tuong: operator-requested preview; image alignment confirmed, world frame unvalidated, 2026-09-05",
    "wdev_b": "Quang Ngai: stationary F4/G3 references and separate G4 peninsula check, 2026-09-05",
    "wdev_c": "Hue Outskirts: operator-requested preview; image alignment confirmed, world frame unvalidated, 2026-09-05",
    "wdev_d": "Dak To Airfield: operator-requested preview; image alignment confirmed, world frame unvalidated, 2026-09-05",
    "wdev_e": "Cam Ranh Port: operator-requested preview; image alignment confirmed, world frame unvalidated, 2026-09-05",
    "wdev_f": "Thanh Hoa: stationary C8/C7 in-game grid references, 2026-09-05",
}

# Exact IDs of the HLL images shipped in assets/images/tac-maps. Do not enable
# future/unknown maps implicitly just because the server returns coordinates.
HLL_DISPLAY_MAPS = frozenset({
    "carentan", "driel", "elalamein", "elsenbornridge", "foy", "hill400",
    "hurtgenforest", "junobeach", "kharkov", "kursk", "mortain", "omahabeach",
    "purpleheartlane", "remagen", "smolensk", "stalingrad", "stmariedumont",
    "stmereeglise", "tobruk", "utahbeach",
})


def display_projection(game, map_id, calibrations):
    map_id = str(map_id).lower()
    configured = calibrations.get(f"{game}:{map_id}")
    if configured is not None:
        # Never override an operator's explicit per-map configuration.
        return deepcopy(configured)
    if game == "hllv" and map_id in DISPLAY_PREVIEWS:
        source = DISPLAY_PREVIEWS[map_id]
        revision = "hllv-display-preview-20260905-v2"
    elif game == "hll" and map_id in HLL_DISPLAY_MAPS:
        source = (f"{map_id}: operator-enabled HLL tactical image; centred XY "
                  "display frame assumed, metric calibration not supplied, 2026-09-05")
        revision = "hll-display-20260905-v1"
    else:
        return None
    return {
        "verified": False,
        "display_ready": True,
        "quality": "estimated",
        "matrix": [1 / 200000, 0, .5, 0, 1 / 200000, .5],
        "units_per_meter": None,
        "max_error_m": None,
        "source": source,
        "map_id": map_id,
        "revision": revision,
    }


def projection_ready(calibration):
    return bool(calibration and (calibration.get("verified") is True or (
        calibration.get("display_ready") is True
        and calibration.get("quality") == "estimated"
    )))
