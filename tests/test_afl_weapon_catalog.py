import pytest

from rcon.game.hll.profile import HLL_PROFILE
from rcon.maps import Team
from rcon.models import calc_weapon_type_usage
from rcon.report_admin_evidence import weapon_category
from rcon.weapons import WEAPON_SIDE_MAP, WeaponType


@pytest.mark.parametrize(
    ("weapon", "kind", "side"),
    [
        ("M1903A4 SPRINGFIELD", WeaponType.Sniper, Team.ALLIES),
        ("M1903A3 SPRINGFIELD", WeaponType.Infantry, Team.ALLIES),
        ("M1 GARAND W/ M7 RGL", WeaponType.Grenade, Team.ALLIES),
        ("KARABINER 98K W/ SCHIESSBECHER", WeaponType.Grenade, Team.AXIS),
        ("SMLE No.1 Mk III EY", WeaponType.Grenade, Team.ALLIES),
        ("GMC CCKW 353 (Transport)", WeaponType.Armor, Team.ALLIES),
        ("FN-Inglis No.2 Mk I", WeaponType.Infantry, Team.ALLIES),
        ("ROKS-2", WeaponType.Infantry, Team.ALLIES),
        ("COAXIAL M1919", WeaponType.Armor, None),
    ],
)
def test_afl_weapon_catalog_and_consumers(weapon, kind, side):
    assert HLL_PROFILE.weapons[weapon] == kind
    assert WEAPON_SIDE_MAP.get(weapon) == side
    assert calc_weapon_type_usage({weapon: 3}) == {kind.value: 3}
    assert weapon_category(weapon, 1) == kind.value


def test_unknown_does_not_get_a_guessed_classification():
    assert calc_weapon_type_usage({"UNKNOWN": 3, "Unknown": 2}) == {}
    assert weapon_category("UNKNOWN", 1) == "unknown"


def test_observed_afl_counts_are_included_in_type_totals():
    assert calc_weapon_type_usage({
        "M1903A4 SPRINGFIELD": 611,
        "M1903A3 SPRINGFIELD": 100,
        "M1 GARAND W/ M7 RGL": 533,
        "KARABINER 98K W/ SCHIESSBECHER": 280,
        "SMLE No.1 Mk III EY": 68,
        "GMC CCKW 353 (Transport)": 36,
        "FN-Inglis No.2 Mk I": 17,
        "ROKS-2": 6,
        "COAXIAL M1919": 2,
        "UNKNOWN": 288,
        "Unknown": 262,
    }) == {"sniper": 611, "infantry": 123, "grenade": 881, "armor": 38}
