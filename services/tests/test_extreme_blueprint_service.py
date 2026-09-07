from __future__ import annotations

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


def test_non_resource_blueprint_does_not_invent_attribute_benefit():
    service = ExtremeBlueprintService.__new__(ExtremeBlueprintService)
    build = service._blank_build(ExtremeOptimizationService.objective("spell_damage"))

    assert (build.AttributeHealth, build.AttributeMagicka, build.AttributeStamina) == (0, 0, 0)
