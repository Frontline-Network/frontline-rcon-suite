"""Display-only projections, separate from independently verified calibration.

Quang Ngai and Thanh Hoa have paired stationary WorldPosition / in-game-grid
observations suggesting a -100000..100000 XY display frame. The operator has
explicitly requested this provisional display for all six extracted HLLV maps,
confirming alignment of the tactical images with the game maps. Applying the
same world frame to the other four maps remains an unvalidated assumption.
This is NOT decoded map metadata, a measured metre scale, or a <=10 m claim.
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


def display_projection(game, map_id, calibrations):
    map_id = str(map_id).lower()
    configured = calibrations.get(f"{game}:{map_id}")
    if configured is not None:
        # Never override an operator's explicit per-map configuration.
        return deepcopy(configured)
    if game != "hllv" or map_id not in DISPLAY_PREVIEWS:
        return None
    return {
        "verified": False,
        "display_ready": True,
        "quality": "estimated",
        "matrix": [1 / 200000, 0, .5, 0, 1 / 200000, .5],
        "units_per_meter": None,
        "max_error_m": None,
        "source": DISPLAY_PREVIEWS[map_id],
        "map_id": map_id,
        "revision": "hllv-display-preview-20260905-v2",
    }


def projection_ready(calibration):
    return bool(calibration and (calibration.get("verified") is True or (
        calibration.get("display_ready") is True
        and calibration.get("quality") == "estimated"
    )))
