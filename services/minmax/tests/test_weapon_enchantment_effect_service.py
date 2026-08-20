from pathlib import Path

import pytest

from services.minmax.rule_repository import RuleRepository
from services.minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from services.minmax.weapon_enchantment_repository import (
    WeaponEnchantmentRepository,
)


DB_PATH = Path("data/eso.db")

FROST_ENCHANTMENT_ID = 5365
CRUSHING_ENCHANTMENT_ID = 26845
ABSORB_HEALTH_ENCHANTMENT_ID = 43573


def service() -> WeaponEnchantmentEffectService:
    return WeaponEnchantmentEffectService(
        enchantment_repository=WeaponEnchantmentRepository(DB_PATH),
        rule_repository=RuleRepository(DB_PATH),
    )


def test_frost_enchantment_without_trait_preserves_base_value():
    effects = service().resolve_effects(
        FROST_ENCHANTMENT_ID,
    )

    assert len(effects) == 1
    assert effects[0].value == 2534


def test_frost_enchantment_with_infused_legendary_weapon():
    effects = service().resolve_effects(
        FROST_ENCHANTMENT_ID,
        weapon_trait="Infused",
        weapon_quality="Legendary",
    )

    assert len(effects) == 1

    # 2534 * 1.30
    assert effects[0].value == pytest.approx(3294.2)


def test_crushing_enchantment_preserves_combat_metadata():
    effects = service().resolve_effects(
        CRUSHING_ENCHANTMENT_ID,
    )

    assert len(effects) == 1

    effect = effects[0]

    assert effect.effect_type == (
        "physical_spell_resistance_reduction"
    )
    assert effect.value == 1622
    assert effect.target == "target"
    assert effect.duration_value == 5
    assert effect.duration_unit == "seconds"


def test_absorb_health_preserves_multiple_effects():
    effects = service().resolve_effects(
        ABSORB_HEALTH_ENCHANTMENT_ID,
    )

    assert len(effects) == 2

    damage = next(
        effect
        for effect in effects
        if effect.effect_type == "damage"
    )

    restore = next(
        effect
        for effect in effects
        if effect.effect_type == "health_restore"
    )

    assert damage.value == 1900
    assert restore.value == 861

def test_jade_returns_weapon_enchantment_rule():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_enchantment_rules("Jade")

    assert len(effects) == 1
    assert effects[0].rule_type == "weapon_enchantment_effect"
    assert effects[0].value == 10
    assert effects[0].unit.value == "percent"


def test_fire_opal_does_not_return_as_enchantment_rule():
    repository = RuleRepository(DB_PATH)

    effects = repository.get_weapon_enchantment_rules("Fire Opal")

    assert effects == []

def test_jade_modifies_weapon_enchantment():
    effects = service().resolve_effects(
        FROST_ENCHANTMENT_ID,
        weapon_trait="Jade",
    )

    assert len(effects) == 1

    # 2534 * 1.10
    assert effects[0].value == pytest.approx(2787.4)    


def test_jade_returns_all_applicable_rules():

    service_instance = service()

    rules = service_instance.get_applicable_rules(
        weapon_trait="Jade",
    )

    assert len(rules) == 2

    assert {
        rule.rule_type
        for rule in rules
    } == {
        "weapon_enchantment_effect",
        "enchantment_cooldown_reduction",
    }


def test_infused_returns_enchantment_rule():

    service_instance = service()

    rules = service_instance.get_applicable_rules(
        weapon_trait="Infused",
        weapon_quality="Legendary",
    )

    assert len(rules) == 1

    assert rules[0].rule_type == "enchantment_effect"
    assert rules[0].value == 30