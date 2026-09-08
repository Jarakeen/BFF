from __future__ import annotations

from minmax.character_build.weapon_type import WeaponType


# Canonical ESO WEAPONTYPE_* numeric identities carried by the imported
# gear_set_piece.weapon_type column. Keep this mapping centralized so saved-build
# weapon identity, set-piece legality, and arena/package search use one bridge.
ESO_WEAPON_TYPE_ID_BY_WEAPON_TYPE: dict[WeaponType, int] = {
    WeaponType.AXE: 1,
    WeaponType.MACE: 2,
    WeaponType.SWORD: 3,
    WeaponType.GREATSWORD: 4,
    WeaponType.BATTLEAXE: 5,
    WeaponType.MAUL: 6,
    WeaponType.SHIELD: 7,
    WeaponType.BOW: 8,
    WeaponType.RESTORATION_STAFF: 9,
    WeaponType.DAGGER: 11,
    WeaponType.FLAME_STAFF: 12,
    WeaponType.FROST_STAFF: 13,
    WeaponType.LIGHTNING_STAFF: 15,
}


def eso_weapon_type_id(weapon_type: WeaponType) -> int | None:
    """Return the imported ESO weapon-type id for one canonical weapon type.

    ``WeaponType.NONE`` deliberately resolves to ``None`` because it represents
    absence of equipment, not an ESO weapon item. Unknown future enum members
    likewise fail closed instead of being coerced into a nearby family.
    """

    return ESO_WEAPON_TYPE_ID_BY_WEAPON_TYPE.get(weapon_type)
