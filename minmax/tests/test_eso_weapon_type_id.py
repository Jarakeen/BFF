from minmax.character_build.weapon_type import WeaponType
from minmax.eso_weapon_type_id import (
    ESO_WEAPON_TYPE_ID_BY_WEAPON_TYPE,
    eso_weapon_type_id,
    eso_weapon_type_id_from_saved_name,
    weapon_type_from_saved_name,
)


def test_maps_canonical_weapon_types_to_imported_eso_ids():
    assert eso_weapon_type_id(WeaponType.AXE) == 1
    assert eso_weapon_type_id(WeaponType.MACE) == 2
    assert eso_weapon_type_id(WeaponType.SWORD) == 3
    assert eso_weapon_type_id(WeaponType.GREATSWORD) == 4
    assert eso_weapon_type_id(WeaponType.BATTLEAXE) == 5
    assert eso_weapon_type_id(WeaponType.MAUL) == 6
    assert eso_weapon_type_id(WeaponType.SHIELD) == 7
    assert eso_weapon_type_id(WeaponType.BOW) == 8
    assert eso_weapon_type_id(WeaponType.RESTORATION_STAFF) == 9
    assert eso_weapon_type_id(WeaponType.DAGGER) == 11
    assert eso_weapon_type_id(WeaponType.FLAME_STAFF) == 12
    assert eso_weapon_type_id(WeaponType.FROST_STAFF) == 13
    assert eso_weapon_type_id(WeaponType.LIGHTNING_STAFF) == 15


def test_saved_weapon_names_resolve_to_exact_canonical_subtypes():
    assert weapon_type_from_saved_name("Restoration Staff") is WeaponType.RESTORATION_STAFF
    assert eso_weapon_type_id_from_saved_name("Restoration Staff") == 9
    assert eso_weapon_type_id_from_saved_name("Bow") == 8
    assert eso_weapon_type_id_from_saved_name("Inferno Staff") == 12
    assert eso_weapon_type_id_from_saved_name("Ice Staff") == 13
    assert eso_weapon_type_id_from_saved_name("Lightning Staff") == 15


def test_aggregate_or_empty_saved_weapon_names_fail_closed():
    assert WeaponType.NONE not in ESO_WEAPON_TYPE_ID_BY_WEAPON_TYPE
    assert eso_weapon_type_id(WeaponType.NONE) is None
    assert eso_weapon_type_id_from_saved_name("") is None
    assert eso_weapon_type_id_from_saved_name("Two-Handed") is None
    assert eso_weapon_type_id_from_saved_name("Dual Wield") is None
