from dataclasses import dataclass

from .calculation import CalculationResult
from .combat_calculation import CombatEffectResult
from .combat_contribution import CombatContribution
from .combat_effect_classifier import (
    DAMAGE_EFFECT_TYPES,
    HEALING_EFFECT_TYPES,
)


@dataclass(frozen=True)
class BuildEvaluation:
    """Resolved evaluation of a single build."""

    stats: CalculationResult
    combat_effects: tuple[CombatEffectResult, ...]
    combat_contributions: tuple[CombatContribution, ...]

    @property
    def total_damage_contribution(self) -> float:
        return sum(
            contribution.effective_value
            for contribution in self.combat_contributions
            if contribution.effect_type in DAMAGE_EFFECT_TYPES
        )

    @property
    def total_healing_contribution(self) -> float:
        return sum(
            contribution.effective_value
            for contribution in self.combat_contributions
            if contribution.effect_type in HEALING_EFFECT_TYPES
        )