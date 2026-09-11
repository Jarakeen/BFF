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


def test_remaining_reviewed_weapon_passives_are_classified_by_effect_layer():
    by_identity = {
        (rule.skill_line, rule.passive): rule.layer
        for rule in VERIFIED_WEAPON_PASSIVE_RULES
    }
    assert by_identity[("Bow", "Ranger")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Dual Wield", "Ambidextrous")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("Dual Wield", "Controlled Fury")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Dual Wield", "Focused Killer")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Dual Wield", "Ruffian")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("One Hand and Shield", "Battlefield Mobility")] is WeaponPassiveLayer.BLOCK_STATE
    assert by_identity[("Two Handed", "Balanced Blade")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Two Handed", "Forceful")] is WeaponPassiveLayer.COMBAT_STATE


def test_ambidextrous_is_the_only_reviewed_new_shared_standing_weapon_passive():
    rows = shared_standing_weapon_passives("Dual Wield")
    assert [(row.skill_line, row.passive) for row in rows] == [("Dual Wield", "Ambidextrous")]
