"""Independent map-side oracle, plus anonymized HLL1 incident samples.

Directions: timraay/hllrcon commit 35d428a0686bf21e759e18a6f27a4b949528c40c.
HLLV identifiers below are those supported by our pinned 2.0.0.0 dependency.
These checks validate geometry against the catalog, not live play on every map.
"""

import hllrcon
import pytest
from hllrcon.data.maps import CardinalDirection

from rcon.automods.geofence import is_outside_combat_area

# map ID, attack coordinate (X=0/Y=1), Allied advance sign, grid size in cm.
# Keep this oracle independent of the production resolver and its overrides.
HLL_SIDES = [
    ("carentan", 0, 1, 20_160),
    ("driel", 1, -1, 19_840),
    ("elalamein", 0, -1, 19_840),
    ("elsenbornridge", 1, 1, 20_000),
    ("foy", 1, -1, 19_840),
    ("hill400", 0, 1, 19_840),
    ("hurtgenforest", 0, 1, 19_840),
    ("junobeach", 1, 1, 20_000),
    ("kharkov", 1, 1, 19_840),
    ("kursk", 1, 1, 19_840),
    ("mortain", 0, 1, 20_000),
    ("omahabeach", 0, -1, 19_840),
    ("purpleheartlane", 1, 1, 19_840),
    ("remagen", 1, -1, 19_840),
    ("smolensk", 0, -1, 20_000),
    ("stmariedumont", 1, 1, 19_840),
    ("stmereeglise", 0, -1, 19_840),
    ("stalingrad", 0, -1, 19_840),
    ("tobruk", 0, -1, 20_000),
    ("utahbeach", 0, -1, 19_840),
]
HLLV_SIDES = [
    ("WDEV_A", 0, -1, 19_840),
    ("WDEV_B", 0, 1, 19_840),
    ("WDEV_C", 1, -1, 19_840),
    ("WDEV_D", 0, 1, 19_840),
    ("WDEV_E", 0, 1, 19_840),
    ("WDEV_F", 1, -1, 19_840),
]
SIDES = HLL_SIDES + HLLV_SIDES


@pytest.mark.parametrize(
    "catalog,oracle", [(hllrcon.HLLMap, HLL_SIDES), (hllrcon.HLLVMap, HLLV_SIDES)]
)
def test_every_supported_map_has_an_independent_side_fixture(catalog, oracle):
    assert {m.id for m in catalog.all()} == {m[0] for m in oracle}


@pytest.mark.parametrize("map_id,coordinate,allied_sign,grid", SIDES)
@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize("max_caps", [2, 3, 4])
def test_own_hq_and_exact_sector_boundary(
    map_id, coordinate, allied_sign, grid, team, max_caps
):
    sign = allied_sign if team == "allies" else -allied_sign

    def outside(value):
        # The perpendicular coordinate must not affect the allowed side.
        pos = [87_000.0, -87_000.0, 100.0]
        pos[coordinate] = value
        return is_outside_combat_area(
            tuple(pos), map_id=map_id, team=team, max_caps=max_caps
        )

    assert outside(-sign * 4.9 * grid) is False  # own HQ
    assert outside(sign * 4.9 * grid) is True  # enemy HQ
    boundary = sign * (2 * max_caps - 5) * grid
    assert outside(boundary - sign) is False
    assert outside(boundary + sign) is True
    # Preserve the original grid's half-open cells (not a global inversion).
    assert outside(boundary) is (sign == 1)
    if max_caps >= 3:
        assert outside(0) is False
        assert outside(-0.9 * grid) is False
        assert outside(0.9 * grid) is False


# Nearest historical samples BEFORE the 21 punishments on HLL1, 2026-09-15
# 16:19:31–16:23:01 UTC, SMDM Warfare. No names, account IDs or sessions retained.
# Each original sample was <=3 seconds old; rounded centimetres are far from
# the boundary. All were on their OWN side, including several HQ spawns.
SMDM_INCIDENT_POSITIONS = [
    ("axis", (-3512, 90634, 308)),
    ("axis", (-3437, 90623, 316)),
    ("axis", (46902, 60543, 879)),
    ("axis", (-3339, 91011, 341)),
    ("allies", (-17193, -80474, 280)),
    ("allies", (14298, -61795, 426)),
    ("allies", (464, -95676, 342)),
    ("allies", (153, -95298, 417)),
    ("axis", (-6432, 57555, 293)),
    ("axis", (20810, 35084, 687)),
    ("axis", (-5925, 77248, 546)),
    ("allies", (-18589, -47875, 127)),
    ("allies", (33503, -25095, 355)),
    ("allies", (-20092, -60824, 153)),
    ("axis", (55, 62775, 534)),
    ("axis", (8017, 59618, 606)),
    ("axis", (3873, 56094, 614)),
    ("axis", (13928, 52448, 605)),
    ("axis", (13776, 52227, 657)),
    ("axis", (14314, 25495, 754)),
    ("axis", (13670, 51854, 617)),
]


@pytest.mark.parametrize("team,position", SMDM_INCIDENT_POSITIONS)
def test_hll1_incident_own_side_is_allowed_but_enemy_side_is_not(team, position):
    assert (
        is_outside_combat_area(position, map_id="stmariedumont", team=team, max_caps=3)
        is False
    )
    opposite = "axis" if team == "allies" else "allies"
    assert (
        is_outside_combat_area(
            position, map_id="stmariedumont", team=opposite, max_caps=3
        )
        is True
    )


@pytest.mark.parametrize("map_id", ["stmariedumont", "STMARIEDUMONT", "StMarieDuMont"])
def test_corrected_map_id_is_case_insensitive(map_id):
    assert (
        is_outside_combat_area(
            (0, -90_000, 100), map_id=map_id, team="allies", max_caps=3
        )
        is False
    )


def test_does_not_mutate_shared_library_map_objects():
    before = [m.model_dump() for m in hllrcon.HLLMap.all() + hllrcon.HLLVMap.all()]
    for map_id, _, _, _ in SIDES:
        for team in ("allies", "axis"):
            is_outside_combat_area((0, 0, 100), map_id=map_id, team=team, max_caps=3)
    assert before == [
        m.model_dump() for m in hllrcon.HLLMap.all() + hllrcon.HLLVMap.all()
    ]


@pytest.mark.parametrize(
    "map_id", ["stmariedumont", "purpleheartlane", "kursk", "kharkov", "elsenbornridge"]
)
def test_already_corrected_dependency_is_not_inverted_again(monkeypatch, map_id):
    corrected = hllrcon.HLLMap.by_id(map_id).model_copy(
        update={"allies_direction": CardinalDirection.TOP_TO_BOTTOM}
    )
    monkeypatch.setattr(hllrcon.HLLMap, "by_id", lambda _: corrected)
    assert (
        is_outside_combat_area(
            (0, -90_000, 100), map_id=map_id, team="allies", max_caps=3
        )
        is False
    )
    assert (
        is_outside_combat_area((0, 90_000, 100), map_id=map_id, team="axis", max_caps=3)
        is False
    )
