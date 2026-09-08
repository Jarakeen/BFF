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

_SAVED_WEAPON_TYPE_BY_NAME: dict[str, WeaponType] = {
    "axe": WeaponType.AXE,
    "mace": WeaponType.MACE,
    "sword": WeaponType.SWORD,
    "greatsword": WeaponType.GREATSWORD,
    "battleaxe": WeaponType.BATTLEAXE,
    "battle axe": WeaponType.BATTLEAXE,
    "maul": WeaponType.MAUL,
    "shield": WeaponType.SHIELD,
    "bow": WeaponType.BOW,
    "restoration staff": WeaponType.RESTORATION_STAFF,
    "resto staff": WeaponType.RESTORATION_STAFF,
    "dagger": WeaponType.DAGGER,
    "inferno staff": WeaponType.FLAME_STAFF,
    "fire staff": WeaponType.FLAME_STAFF,
    "flame staff": WeaponType.FLAME_STAFF,
    "ice staff": WeaponType.FROST_STAFF,
    "frost staff": WeaponType.FROST_STAFF,
    "lightning staff": WeaponType.LIGHTNING_STAFF,
    "shock staff": WeaponType.LIGHTNING_STAFF,
}


def eso_weapon_type_id(weapon_type: WeaponType) -> int | None:
    """Return the imported ESO weapon-type id for one canonical weapon type.

    ``WeaponType.NONE`` deliberately resolves to ``None`` because it represents
    absence of equipment, not an ESO weapon item. Unknown future enum members
    likewise fail closed instead of being coerced into a nearby family.
    """

    return ESO_WEAPON_TYPE_ID_BY_WEAPON_TYPE.get(weapon_type)


def weapon_type_from_saved_name(value: object) -> WeaponType | None:
    """Resolve one saved-build weapon label to canonical ``WeaponType``.

    Legacy aggregate labels such as ``Two-Handed`` or ``Dual Wield`` are not
    concrete weapon subtypes and intentionally return ``None``.
    """

    key = " ".join(str(value or "").strip().casefold().split())
    return _SAVED_WEAPON_TYPE_BY_NAME.get(key)


def eso_weapon_type_id_from_saved_name(value: object) -> int | None:
    weapon_type = weapon_type_from_saved_name(value)
    if weapon_type is None:
        return None
    return eso_weapon_type_id(weapon_type)
