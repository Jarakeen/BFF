from dataclasses import dataclass

from .effects import EffectUnit
from .rule_effects import RuleEffect


@dataclass(frozen=True)
class ModifierContribution:
    source: str
    percentage: float
    contribution: float


@dataclass(frozen=True)
class EnchantmentCalculation:
    base_value: float
    final_value: float
    modifiers: list[ModifierContribution]


def calculate_enchantment_effect(
    *,
    base_value: float,
    rules: list[RuleEffect],
) -> EnchantmentCalculation:

    percentage = 0.0
    modifiers: list[ModifierContribution] = []

    for rule in rules:
        if rule.rule_type not in {
            "enchantment_effect",
            "weapon_enchantment_effect",
        }:
            continue

        if rule.unit != EffectUnit.PERCENT:
            continue

        contribution = base_value * (
            rule.value / 100.0
        )

        percentage += rule.value

        modifiers.append(
            ModifierContribution(
                source=rule.source,
                percentage=rule.value,
                contribution=contribution,
            )
        )

    final_value = base_value * (
        1.0 + percentage / 100.0
    )

    return EnchantmentCalculation(
        base_value=base_value,
        final_value=final_value,
        modifiers=modifiers,
    )


def test_non_percent_rule_does_not_modify_effect_value():
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