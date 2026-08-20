from dataclasses import dataclass

from .effects import EffectUnit
from .rule_effects import RuleEffect


@dataclass(frozen=True)
class CooldownModifier:
    source: str
    percentage: float


def extract_cooldown_modifiers(
    rules: list[RuleEffect],
) -> list[CooldownModifier]:
    """Extract cooldown-reduction rules without applying them."""

    modifiers: list[CooldownModifier] = []

    for rule in rules:
        if rule.rule_type != "enchantment_cooldown_reduction":
            continue

        if rule.unit != EffectUnit.PERCENT:
            continue

        modifiers.append(
            CooldownModifier(
                source=rule.source,
                percentage=rule.value,
            )
        )

    return modifiers


def calculate_cooldown_reduction(
    rules: list[RuleEffect],
) -> float:
    """Calculate total applicable cooldown reduction."""

    modifiers = extract_cooldown_modifiers(rules)

    return sum(
        modifier.percentage
        for modifier in modifiers
    )