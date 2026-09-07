from __future__ import annotations

import pytest

from services.extreme_blueprint_service import ExtremeBlueprintService
from services.extreme_optimization_service import ExtremeOptimizationService


def test_blank_blueprint_is_fully_equipped_for_static_mutation_search():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_damage")

    build = service._blank_build(objective)

    assert build.Name == "Jane / John Doe"
    assert build.BuildName == "Extreme Spell Damage Blueprint"
    assert build.FrontBarWeapon.WeaponType == "Inferno Staff"
    assert build.FrontBarWeapon.Level == "CP160"
    assert build.Necklace.Enchant == "Spell Damage"
    assert build.Ring1.Trait == "Infused"
    assert build.Ring2.Trait == "Infused"
    assert all(entry["Level"] == "CP160" for entry in build.Armor.values())
    assert all(entry["EnchantTier"] == "Truly Superb" for entry in build.Armor.values())


def test_resource_blueprint_starts_with_all_attributes_in_requested_resource():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)

    health = service._blank_build(ExtremeOptimizationService.objective("max_health"))
    magicka = service._blank_build(ExtremeOptimizationService.objective("max_magicka"))
    stamina = service._blank_build(ExtremeOptimizationService.objective("max_stamina"))

    assert (health.AttributeHealth, health.AttributeMagicka, health.AttributeStamina) == (64, 0, 0)
    assert (magicka.AttributeHealth, magicka.AttributeMagicka, magicka.AttributeStamina) == (0, 64, 0)
    assert (stamina.AttributeHealth, stamina.AttributeMagicka, stamina.AttributeStamina) == (0, 0, 64)


def test_non_resource_blueprint_still_allocates_all_64_points():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)

    spell = service._blank_build(ExtremeOptimizationService.objective("spell_damage"))
    weapon = service._blank_build(ExtremeOptimizationService.objective("weapon_damage"))
    armor = service._blank_build(ExtremeOptimizationService.objective("physical_resistance"))

    assert (spell.AttributeHealth, spell.AttributeMagicka, spell.AttributeStamina) == (0, 64, 0)
    assert (weapon.AttributeHealth, weapon.AttributeMagicka, weapon.AttributeStamina) == (0, 0, 64)
    assert (armor.AttributeHealth, armor.AttributeMagicka, armor.AttributeStamina) == (64, 0, 0)


def test_spell_damage_profile_is_sorcerer_with_both_bars_and_dual_swords():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_damage")
    build = service._blank_build(objective)

    profiled, label, candidates = service._apply_resting_profile(
        build,
        objective,
        active_bar="front",
    )

    assert label == "Sorcerer"
    assert candidates == ("Sorcerer",)
    assert profiled.EsoClass == "Sorcerer"
    assert len([skill for skill in profiled.FrontBarSkills if skill]) == 6
    assert len([skill for skill in profiled.BackBarSkills if skill]) == 6
    assert profiled.FrontBarWeapon.WeaponType == "Sword"
    assert profiled.FrontBarOffHand.WeaponType == "Sword"
    assert profiled.BackBarWeapon.WeaponType == "Sword"
    assert profiled.BackBarOffHand.WeaponType == "Sword"
    assert all(entry["Weight"] == "Medium" for entry in profiled.Armor.values())


def test_spell_damage_resting_bonus_counts_expert_mage_swords_and_agility():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_damage")
    build = service._blank_build(objective)
    profiled, _, _ = service._apply_resting_profile(build, objective, active_bar="front")

    bonus = service._resting_spell_damage_bonus(profiled, active_bar="front")

    assert bonus == pytest.approx(((6 * 108) + (2 * 129)) * 1.14)


def test_spell_damage_potion_percent_stacks_additively_with_agility_on_manual_bonus():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_damage")
    build = service._blank_build(objective)
    profiled, _, _ = service._apply_resting_profile(build, objective, active_bar="front")

    bonus = service._resting_spell_damage_bonus(
        profiled,
        active_bar="front",
        extra_percent=0.20,
    )

    assert bonus == pytest.approx(((6 * 108) + (2 * 129)) * 1.34)


def test_spell_damage_profile_uses_same_self_contained_bar_package_on_back_bar():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("spell_damage")
    build = service._blank_build(objective)

    profiled, _, _ = service._apply_resting_profile(build, objective, active_bar="back")

    assert len([skill for skill in profiled.FrontBarSkills if skill]) == 6
    assert len([skill for skill in profiled.BackBarSkills if skill]) == 6
    assert profiled.BackBarWeapon.WeaponType == "Sword"
    assert profiled.BackBarOffHand.WeaponType == "Sword"


def test_non_spell_objective_uses_representative_class_when_sheet_math_ties():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    objective = ExtremeOptimizationService.objective("max_health")
    build = service._blank_build(objective)

    profiled, label, candidates = service._apply_resting_profile(build, objective, active_bar="front")

    assert profiled.EsoClass == "Arcanist"
    assert label == "Arcanist (representative top-7 tie)"
    assert len(candidates) == 7
    assert not any(profiled.FrontBarSkills)


def test_objective_specific_potion_profiles_are_explicit():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)

    assert service._potion_profile(ExtremeOptimizationService.objective("spell_damage")) == (
        "Spell Power potion",
        "Major Sorcery",
    )
    assert service._potion_profile(ExtremeOptimizationService.objective("spell_critical")) == (
        "Spell Critical potion",
        "Major Prophecy",
    )
    assert service._potion_profile(ExtremeOptimizationService.objective("physical_resistance")) == (
        "Increase Armor potion",
        "Major Resolve",
    )
    assert service._potion_profile(ExtremeOptimizationService.objective("max_health")) == (
        "No potion improves this objective",
        "",
    )
