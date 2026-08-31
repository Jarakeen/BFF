from __future__ import annotations

from dataclasses import dataclass

from minmax.skill_coefficient import (
    SkillCoefficientResult,
    evaluate_skill_coefficient,
)
from minmax.skill_coefficients import is_inactive_skill_coefficient
from minmax.skill_coefficient_service import (
    SkillCoefficientService,
)


@dataclass(frozen=True)
class SkillDamageResult:
    """
    Raw damage produced by one ESO skill before
    critical damage, penetration, and mitigation.
    """

    skill_rank_id: int
    components: tuple[SkillCoefficientResult, ...]
    total_raw_damage: float


class SkillDamageService:
    """
    Evaluates all active coefficient components for
    one skill rank.
    """

    def __init__(
        self,
        coefficient_service: SkillCoefficientService,
    ):
        self.coefficient_service = (
            coefficient_service
        )

    def evaluate(
        self,
        skill_rank_id: int,
        *,
        max_stat: float,
        power: float,
    ) -> SkillDamageResult:

        coefficients = (
            self.coefficient_service
            .get_for_skill_rank(
                skill_rank_id
            )
        )

        # Only UESP's exact -1/-1/-1/-1 empty-slot marker is inactive.
        # Negative coefficient terms can be real mechanics and must remain
        # available to the evaluator.
        active_coefficients = tuple(
            coefficient
            for coefficient in coefficients
            if not is_inactive_skill_coefficient(coefficient)
        )

        components = tuple(
            evaluate_skill_coefficient(
                coefficient,
                max_stat=max_stat,
                power=power,
            )
            for coefficient in active_coefficients
        )

        total_raw_damage = sum(
            component.scaled_value
            for component in components
        )

        return SkillDamageResult(
            skill_rank_id=skill_rank_id,
            components=components,
            total_raw_damage=total_raw_damage,
        )
