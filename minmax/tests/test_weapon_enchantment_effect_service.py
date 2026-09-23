from pathlib import Path

import pytest

from minmax.rule_repository import RuleRepository
from minmax.weapon_enchantment_effect_service import (
    WeaponEnchantmentEffectService,
)
from minmax.weapon_enchantment_repository import (
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

    assert len(rules) == 2

    by_type = {rule.rule_type: rule for rule in rules}
    assert by_type["enchantment_effect"].value == 30
    assert by_type["enchantment_cooldown_reduction"].value == 50


def test_infused_gold_alias_uses_legendary_magnitude_and_cooldown_rule():
    rules = service().get_applicable_rules(
        weapon_trait="Infused",
        weapon_quality="Gold",
    )

    by_type = {rule.rule_type: rule for rule in rules}
    assert by_type["enchantment_effect"].value == 30
    assert by_type["enchantment_cooldown_reduction"].value == 50


def test_infused_reduces_weapon_enchantment_cooldown_by_fifty_percent():
    result = service().resolve_cooldown(
        base_cooldown=10.0,
        weapon_trait="Infused",
        weapon_quality="Gold",
    )

    assert result.base_cooldown == 10.0
    assert result.reduction == 50.0
    assert result.final_cooldown == 5.0



def test_trait_adjustment_preserves_enchantment_scaling_metadata():
    from minmax.combat_effects import CombatEffect
    from minmax.effects import EffectUnit

    class _Repository:
        def get_effects(self, _item_id, *, use_max_value=True):
            assert use_max_value is True
            return [
                CombatEffect(
                    effect_type="damage",
                    value=100.0,
                    source="Damage Health",
                    unit=EffectUnit.FLAT,
                    damage_type="oblivion",
                    target="target",
                    scaling_type="target_max_health",
                    condition="reviewed-condition",
                )
            ]

    class _Rules:
        def get_infused_effect(self, *, gear_type, quality):
            from minmax.rule_effects import RuleEffect
            assert gear_type == "Weapon"
            assert quality == "Legendary"
            return RuleEffect(
                rule_type="enchantment_effect",
                value=30.0,
                source="Infused",
                unit=EffectUnit.PERCENT,
                target_system="enchantment",
            )

        def get_infused_weapon_cooldown_effect(self):
            from minmax.rule_effects import RuleEffect
            return RuleEffect(
                rule_type="enchantment_cooldown_reduction",
                value=50.0,
                source="Infused",
                unit=EffectUnit.PERCENT,
                target_system="weapon_enchantment",
            )

    result = WeaponEnchantmentEffectService(
        _Repository(),
        _Rules(),
    ).resolve_effects(
        1,
        weapon_trait="Infused",
        weapon_quality="Legendary",
    )

    assert len(result) == 1
    assert result[0].scaling_type == "target_max_health"
    assert result[0].condition == "reviewed-condition"
