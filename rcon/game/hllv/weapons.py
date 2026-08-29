"""HLL Vietnam combat-weapon classifications and team associations.

``hllrcon`` generates its HLLV reference objects from the game's reference
data.  Keeping this compatibility layer derived from those objects avoids a
second, manually maintained list and preserves the exact identifiers emitted
by the game server in kill logs.

The reference data also contains bandages, supplies and construction tools.
Those entries cannot meaningfully be restricted by the seeding kill rule and
are deliberately omitted from the settings catalogue.
"""

from hllrcon import HLLVFaction, HLLVWeapon
from hllrcon import WeaponType as ReferenceWeaponType

from rcon.maps import Team
from rcon.weapons import WeaponType

_REFERENCE_TYPE_MAP: dict[ReferenceWeaponType, WeaponType] = {
    ReferenceWeaponType.BOLT_ACTION_RIFLE: WeaponType.Infantry,
    ReferenceWeaponType.SEMI_AUTO_RIFLE: WeaponType.Infantry,
    ReferenceWeaponType.ASSAULT_RIFLE: WeaponType.Infantry,
    ReferenceWeaponType.SUBMACHINE_GUN: WeaponType.Infantry,
    ReferenceWeaponType.SHOTGUN: WeaponType.Infantry,
    ReferenceWeaponType.PISTOL: WeaponType.Infantry,
    ReferenceWeaponType.REVOLVER: WeaponType.Infantry,
    ReferenceWeaponType.FLAMETHROWER: WeaponType.Infantry,
    ReferenceWeaponType.MELEE: WeaponType.Infantry,
    ReferenceWeaponType.ANTI_MATERIEL_RIFLE: WeaponType.Infantry,
    ReferenceWeaponType.MACHINE_GUN: WeaponType.MachineGun,
    ReferenceWeaponType.GRENADE: WeaponType.Grenade,
    ReferenceWeaponType.GRENADE_LAUNCHER: WeaponType.Grenade,
    ReferenceWeaponType.AP_MINE: WeaponType.Mine,
    ReferenceWeaponType.AT_MINE: WeaponType.Mine,
    ReferenceWeaponType.ROCKET_LAUNCHER: WeaponType.Bazooka,
    ReferenceWeaponType.AT_GUN: WeaponType.PAK,
    ReferenceWeaponType.TANK_CANNON: WeaponType.Armor,
    ReferenceWeaponType.TANK_COAXIAL_MG: WeaponType.Armor,
    ReferenceWeaponType.TANK_HULL_MG: WeaponType.Armor,
    ReferenceWeaponType.TANK_RECON: WeaponType.Armor,
    ReferenceWeaponType.MOUNTED_MG: WeaponType.Armor,
    ReferenceWeaponType.ROADKILL: WeaponType.Armor,
    ReferenceWeaponType.ARTILLERY: WeaponType.Artillery,
    ReferenceWeaponType.MORTAR: WeaponType.Artillery,
    ReferenceWeaponType.COMMANDER_ABILITY: WeaponType.Commander,
    ReferenceWeaponType.SATCHEL: WeaponType.Satchel,
}


def _classify_weapon(weapon: HLLVWeapon) -> WeaponType | None:
    """Map detailed HLLV types to CRCON's stable, coarse categories."""

    if (
        weapon.magnification
        and weapon.magnification > 1
        and weapon.type
        in {
            ReferenceWeaponType.BOLT_ACTION_RIFLE,
            ReferenceWeaponType.SEMI_AUTO_RIFLE,
            ReferenceWeaponType.ANTI_MATERIEL_RIFLE,
        }
    ):
        return WeaponType.Sniper
    return _REFERENCE_TYPE_MAP.get(weapon.type)


def _logical_team(weapon: HLLVWeapon) -> Team | None:
    """Return a logical CRCON side only for faction-exclusive weapons."""

    is_allies = HLLVFaction.US in weapon.factions
    is_axis = HLLVFaction.NVA in weapon.factions
    if is_allies == is_axis:
        return None
    return Team.ALLIES if is_allies else Team.AXIS


HLLV_WEAPONS: dict[str, WeaponType] = {}
HLLV_WEAPON_SIDES: dict[str, Team] = {}

for _weapon in HLLVWeapon.all():
    _weapon_type = _classify_weapon(_weapon)
    if _weapon_type is None:
        continue

    HLLV_WEAPONS[_weapon.id] = _weapon_type
    if _team := _logical_team(_weapon):
        HLLV_WEAPON_SIDES[_weapon.id] = _team

__all__ = ["HLLV_WEAPONS", "HLLV_WEAPON_SIDES"]
