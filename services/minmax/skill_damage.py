from __future__ import annotations

from dataclasses import dataclass

from services.minmax.skill_coefficient import (
    SkillCoefficientResult,
    evaluate_skill_coefficient,
)
from services.minmax.skill_coefficient_service import (
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

        active_coefficients = tuple(
            coefficient
            for coefficient in coefficients
            if coefficient.type != "-1"
            and coefficient.a >= 0
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