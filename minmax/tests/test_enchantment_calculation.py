from minmax.enchantment_calculation import (
    calculate_enchantment_effect,
)
from minmax.effects import EffectUnit
from minmax.rule_effects import RuleEffect


def test_single_percent_modifier():
    infused = RuleEffect(
        rule_type="enchantment_effect",
        value=30,
        source="Infused",
        unit=EffectUnit.PERCENT,
        target_system="enchantment",
    )

    result = calculate_enchantment_effect(
        base_value=1000,
        rules=[infused],
    )

    assert result.base_value == 1000
    assert result.final_value == 1300
    assert len(result.modifiers) == 1
    assert result.modifiers[0].source == "Infused"
    assert result.modifiers[0].percentage == 30
    assert result.modifiers[0].contribution == 300


def test_multiple_percent_modifiers_stack_additively():
    infused = RuleEffect(
        rule_type="enchantment_effect",
        value=30,
        source="Infused",
        unit=EffectUnit.PERCENT,
        target_system="enchantment",
    )

    jade = RuleEffect(
        rule_type="weapon_enchantment_effect",
        value=10,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_enchantment_effect(
        base_value=1000,
        rules=[infused, jade],
    )

    assert result.final_value == 1400

def test_cooldown_reduction_does_not_modify_effect_value():
    cooldown = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_enchantment_effect(
        base_value=1000,
        rules=[cooldown],
    )

    assert result.final_value == 1000
    assert result.modifiers == []    