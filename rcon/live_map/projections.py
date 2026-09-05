"""Display-only projections, separate from independently verified calibration.

The two HLLV maps below have paired stationary WorldPosition / in-game-grid
observations. Their north-up grid suggests a -100000..100000 XY display frame.
This is NOT decoded map metadata, a measured metre scale, or a <=10 m claim.
Do not apply this frame to other maps just because their texture is also square.
"""
from copy import deepcopy


FIELD_PREVIEWS = {
    "wdev_b": "Quang Ngai: stationary F4/G3 references and separate G4 peninsula check, 2026-09-05",
    "wdev_f": "Thanh Hoa: stationary C8/C7 in-game grid references, 2026-09-05",
}


def display_projection(game, map_id, calibrations):
    map_id = str(map_id).lower()
    configured = calibrations.get(f"{game}:{map_id}")
    if configured is not None:
        # Never override an operator's explicit per-map configuration.
        return deepcopy(configured)
    if game != "hllv" or map_id not in FIELD_PREVIEWS:
        return None
    return {
        "verified": False,
        "display_ready": True,
        "quality": "estimated",
        "matrix": [1 / 200000, 0, .5, 0, 1 / 200000, .5],
        "units_per_meter": None,
        "max_error_m": None,
        "source": FIELD_PREVIEWS[map_id],
        "map_id": map_id,
        "revision": "hllv-field-grid-20260905-v1",
    }


def projection_ready(calibration):
    return bool(calibration and (calibration.get("verified") is True or (
        calibration.get("display_ready") is True
        and calibration.get("quality") == "estimated"
    )))
