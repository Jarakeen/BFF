from minmax.combat_cooldown_rules import (
    calculate_cooldown_from_rules,
)
from minmax.effects import EffectUnit
from minmax.rule_effects import RuleEffect


def test_no_cooldown_rules_preserves_base_cooldown():

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[],
    )

    assert result.base_cooldown == 10
    assert result.reduction == 0
    assert result.final_cooldown == 10


def test_jade_reduces_cooldown_by_fifty_percent():

    jade = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[jade],
    )

    assert result.reduction == 50
    assert result.final_cooldown == 5


def test_enchantment_magnitude_rule_does_not_reduce_cooldown():

    jade_magnitude = RuleEffect(
        rule_type="weapon_enchantment_effect",
        value=10,
        source="Jade",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[jade_magnitude],
    )

    assert result.reduction == 0
    assert result.final_cooldown == 10


def test_infused_magnitude_rule_does_not_reduce_cooldown():

    infused = RuleEffect(
        rule_type="enchantment_effect",
        value=30,
        source="Infused",
        unit=EffectUnit.PERCENT,
        target_system="enchantment",
    )

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[infused],
    )

    assert result.reduction == 0
    assert result.final_cooldown == 10


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

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[jade, other],
    )

    assert result.reduction == 60
    assert result.final_cooldown == 4


def test_cooldown_reduction_is_capped_at_one_hundred_percent():

    first = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=80,
        source="First",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    second = RuleEffect(
        rule_type="enchantment_cooldown_reduction",
        value=50,
        source="Second",
        unit=EffectUnit.PERCENT,
        target_system="weapon_enchantment",
    )

    result = calculate_cooldown_from_rules(
        base_cooldown=10,
        rules=[first, second],
    )

    assert result.reduction == 100
    assert result.final_cooldown == 0