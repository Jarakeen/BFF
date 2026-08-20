from dataclasses import dataclass

from .effects import EffectUnit
from .rule_effects import RuleEffect


@dataclass(frozen=True)
class CooldownRuleResult:
    base_cooldown: float
    reduction: float
    final_cooldown: float


def calculate_cooldown_from_rules(
    *,
    base_cooldown: float,
    rules: list[RuleEffect],
) -> CooldownRuleResult:
    """Apply applicable cooldown-reduction rules to a base cooldown."""

    if base_cooldown < 0:
        raise ValueError("Cooldown cannot be negative.")

    reduction = 0.0

    for rule in rules:
        if rule.rule_type != "enchantment_cooldown_reduction":
            continue

        if rule.unit != EffectUnit.PERCENT:
            continue

        reduction += rule.value

    if reduction > 100.0:
        reduction = 100.0

    final_cooldown = base_cooldown * (
        1.0 - reduction / 100.0
    )

    return CooldownRuleResult(
        base_cooldown=base_cooldown,
        reduction=reduction,
        final_cooldown=final_cooldown,
    )