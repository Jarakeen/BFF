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
    assert by_identity[("Bow", "Accuracy")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("Bow", "Vinedusk Training")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Bow", "Hawk Eye")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Bow", "Hasty Retreat")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Bow", "Ranger")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Dual Wield", "Ambidextrous")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("Dual Wield", "Twin Blade and Blunt")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("Dual Wield", "Controlled Fury")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Dual Wield", "Focused Killer")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Dual Wield", "Ruffian")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("One Hand and Shield", "Deadly Bash")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("One Hand and Shield", "Deflect Bolts")] is WeaponPassiveLayer.BLOCK_STATE
    assert by_identity[("One Hand and Shield", "Fortress")] is WeaponPassiveLayer.BLOCK_STATE
    assert by_identity[("One Hand and Shield", "Sword and Board")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("One Hand and Shield", "Battlefield Mobility")] is WeaponPassiveLayer.BLOCK_STATE
    assert by_identity[("Two Handed", "Balanced Blade")] is WeaponPassiveLayer.ABILITY_FAMILY
    assert by_identity[("Two Handed", "Heavy Weapons")] is WeaponPassiveLayer.SHARED_STANDING
    assert by_identity[("Two Handed", "Follow Up")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Two Handed", "Battle Rush")] is WeaponPassiveLayer.COMBAT_STATE
    assert by_identity[("Two Handed", "Forceful")] is WeaponPassiveLayer.COMBAT_STATE


def test_reviewed_shared_standing_weapon_passives_are_explicit_by_line():
    assert [row.passive for row in shared_standing_weapon_passives("Bow")] == ["Accuracy"]
    assert [row.passive for row in shared_standing_weapon_passives("Dual Wield")] == [
        "Ambidextrous",
        "Twin Blade and Blunt",
    ]
    assert [row.passive for row in shared_standing_weapon_passives("One Hand and Shield")] == [
        "Sword and Board",
    ]
    assert [row.passive for row in shared_standing_weapon_passives("Two Handed")] == [
        "Heavy Weapons",
    ]
