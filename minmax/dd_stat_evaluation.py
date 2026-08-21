from dataclasses import dataclass

from .calculation import CalculationResult
from .evaluation_context import EvaluationContext


@dataclass(frozen=True)
class DDStatEvaluation:
    """Effective offensive statistics for a DD encounter."""

    weapon_damage: float
    spell_damage: float

    physical_penetration: float
    spell_penetration: float

    effective_physical_penetration: float
    effective_spell_penetration: float

    physical_overpenetration: float
    spell_overpenetration: float

    critical_chance: float
    effective_critical_chance: float
    critical_chance_excess: float

    critical_damage: float
    effective_critical_damage: float
    critical_damage_excess: float


def evaluate_dd_stats(
    calculation: CalculationResult,
    context: EvaluationContext,
    *,
    penetration_cap: float = 18200.0,
    critical_chance_cap: float = 100.0,
    critical_damage_cap: float = 125.0,
) -> DDStatEvaluation:
    """Evaluate offensive stats against an encounter context."""

    weapon_damage = calculation.value("weapon_damage")
    spell_damage = calculation.value("spell_damage")

    physical_penetration = calculation.value(
        "physical_penetration"
    )
    spell_penetration = calculation.value(
        "spell_penetration"
    )

    target_resistance = context.target_resistance

    if target_resistance is None:
        effective_physical_penetration = physical_penetration
        effective_spell_penetration = spell_penetration

        physical_overpenetration = 0.0
        spell_overpenetration = 0.0
    else:
        physical_limit = min(
            penetration_cap,
            target_resistance,
        )

        spell_limit = min(
            penetration_cap,
            target_resistance,
        )

        effective_physical_penetration = min(
            physical_penetration,
            physical_limit,
        )

        effective_spell_penetration = min(
            spell_penetration,
            spell_limit,
        )

        physical_overpenetration = max(
            0.0,
            physical_penetration - physical_limit,
        )

        spell_overpenetration = max(
            0.0,
            spell_penetration - spell_limit,
        )

    critical_chance = calculation.value(
        "critical_chance"
    )

    effective_critical_chance = min(
        critical_chance,
        critical_chance_cap,
    )

    critical_chance_excess = max(
        0.0,
        critical_chance - critical_chance_cap,
    )

    critical_damage = calculation.value(
        "critical_damage"
    )

    effective_critical_damage = min(
        critical_damage,
        critical_damage_cap,
    )

    critical_damage_excess = max(
        0.0,
        critical_damage - critical_damage_cap,
    )

    return DDStatEvaluation(
        weapon_damage=weapon_damage,
        spell_damage=spell_damage,
        physical_penetration=physical_penetration,
        spell_penetration=spell_penetration,
        effective_physical_penetration=effective_physical_penetration,
        effective_spell_penetration=effective_spell_penetration,
        physical_overpenetration=physical_overpenetration,
        spell_overpenetration=spell_overpenetration,
        critical_chance=critical_chance,
        effective_critical_chance=effective_critical_chance,
        critical_chance_excess=critical_chance_excess,
        critical_damage=critical_damage,
        effective_critical_damage=effective_critical_damage,
        critical_damage_excess=critical_damage_excess,
    )