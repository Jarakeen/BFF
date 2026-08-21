from minmax.combat_rule_calculation import (
    calculate_cooldown_reduction,
    extract_cooldown_modifiers,
)
from minmax.effects import EffectUnit
from minmax.rule_effects import RuleEffect


def test_extracts_cooldown_reduction_rule():

    jade = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    modifiers = extract_cooldown_modifiers([jade])

    assert len(modifiers) == 1
    assert modifiers[0].source == "Jade"
    assert modifiers[0].percentage == 50


def test_ignores_enchantment_magnitude_rules():

    jade = RuleEffect(
        rule_type="weapon_enchantment_effect",
        value=10,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    modifiers = extract_cooldown_modifiers([jade])

    assert modifiers == []


def test_ignores_non_percent_cooldown_rules():

    rule = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Test",
        unit=EffectUnit.FLAT,
        target_system="weapon_enchantment",
    )

    modifiers = extract_cooldown_modifiers([rule])

    assert modifiers == []


def test_multiple_cooldown_reductions_stack_additively():

    jade = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    other = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=10,
        source="Other",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_cooldown_reduction(
        [jade, other],
    )

    assert result == 60


def test_no_cooldown_rules_returns_zero():

    result = calculate_cooldown_reduction([])

    assert result == 0