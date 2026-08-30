from minmax.weapon_passive_classification import (
    VERIFIED_WEAPON_PASSIVE_RULES,
    WeaponPassiveLayer,
    shared_standing_weapon_passives,
)


def test_restoration_staff_has_no_generic_shared_standing_passive():
    assert shared_standing_weapon_passives("Restoration Staff") == ()


def test_destruction_staff_has_no_generic_shared_standing_passive():
    assert shared_standing_weapon_passives("Destruction Staff") == ()


def test_restoration_master_and_penetrating_magic_are_ability_family_specific():
    by_name = {rule.passive: rule for rule in VERIFIED_WEAPON_PASSIVE_RULES}
    assert by_name["Restoration Master"].layer is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_name["Penetrating Magic"].layer is WeaponPassiveLayer.ABILITY_FAMILY


def test_heavy_attack_block_status_and_event_passives_stay_out_of_shared_sheet():
    by_name = {rule.passive: rule for rule in VERIFIED_WEAPON_PASSIVE_RULES}
    assert by_name["Essence Drain"].layer is WeaponPassiveLayer.COMBAT_STATE
    assert by_name["Cycle of Life"].layer is WeaponPassiveLayer.COMBAT_STATE
    assert by_name["Absorb"].layer is WeaponPassiveLayer.BLOCK_STATE
    assert by_name["Elemental Force"].layer is WeaponPassiveLayer.STATUS_STATE
    assert by_name["Tri Focus"].layer is WeaponPassiveLayer.BLOCK_STATE
    assert by_name["Destruction Expert"].layer is WeaponPassiveLayer.COMBAT_STATE
