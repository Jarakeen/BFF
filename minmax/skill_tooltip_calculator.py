from __future__ import annotations

from dataclasses import dataclass

from .build_calculation_context import BuildCalculationContext
from .skill_coefficient_repository import ResolvedSkillRank, SkillCoefficientRepository
from .skill_coefficients import (
    SkillCoefficientTrace,
    SkillScalingInputs,
    UnsupportedSkillCoefficientType,
    evaluate_skill_coefficient,
)
from .stat_ids import StatId


@dataclass(frozen=True)
class SkillTooltipResult:
    skill: ResolvedSkillRank | None
    scaling: SkillScalingInputs | None
    components: tuple[SkillCoefficientTrace, ...]
    raw_total: float | None
    unresolved: tuple[str, ...] = ()


class SkillTooltipCalculator:
    """Phase 3 raw skill-tooltip foundation.

    This layer resolves coefficient components against the already-calculated
    Phase 2 character state. It intentionally does not apply crit, target
    mitigation, execute rules, CP damage multipliers, passives, or final ESO
    tooltip rounding. Those are separate, auditable combat layers.
    """

    def __init__(self, repository: SkillCoefficientRepository) -> None:
        self.repository = repository

    @staticmethod
    def scaling_from_context(context: BuildCalculationContext) -> SkillScalingInputs:
        if context.core_state is None:
            raise ValueError("core_state is required for skill coefficient evaluation")

        derived = context.core_state.derived
        weapon_damage = derived.get(StatId.WEAPON_DAMAGE)
        spell_damage = derived.get(StatId.SPELL_DAMAGE)
        if weapon_damage is None or spell_damage is None:
            raise ValueError("weapon and spell damage are required for skill coefficient evaluation")

        return SkillScalingInputs(
            max_health=float(context.character_state.max_health),
            max_magicka=float(context.character_state.max_magicka),
            max_stamina=float(context.character_state.max_stamina),
            weapon_damage=float(weapon_damage.final_value),
            spell_damage=float(spell_damage.final_value),
        )

    def evaluate_name(
        self,
        name: str,
        context: BuildCalculationContext,
    ) -> SkillTooltipResult:
        resolution = self.repository.resolve_name(name)
        if resolution.rank is None:
            return SkillTooltipResult(
                skill=None,
                scaling=None,
                components=(),
                raw_total=None,
                unresolved=resolution.unresolved,
            )
        return self._evaluate_resolution(resolution.rank, resolution.unresolved, context)

    def evaluate_ability_id(
        self,
        ability_id: int,
        context: BuildCalculationContext,
    ) -> SkillTooltipResult:
        resolution = self.repository.resolve_ability_id(ability_id)
        if resolution.rank is None:
            return SkillTooltipResult(
                skill=None,
                scaling=None,
                components=(),
                raw_total=None,
                unresolved=resolution.unresolved,
            )
        return self._evaluate_resolution(resolution.rank, resolution.unresolved, context)

    def _evaluate_resolution(
        self,
        skill: ResolvedSkillRank,
        unresolved_seed: tuple[str, ...],
        context: BuildCalculationContext,
    ) -> SkillTooltipResult:
        unresolved = list(unresolved_seed)
        scaling = self.scaling_from_context(context)
        components: list[SkillCoefficientTrace] = []

        for coefficient in skill.coefficients:
            coefficient_type = str(coefficient.type or "").strip()
            if coefficient_type == "-1" or coefficient.a < 0:
                unresolved.append(
                    f"{skill.name}: coefficient {coefficient.coefficient_number} is inactive/sentinel"
                )
                continue
            try:
                trace = evaluate_skill_coefficient(
                    coefficient,
                    max_stat=scaling.highest_max_resource,
                    power=scaling.highest_offensive_power,
                )
            except UnsupportedSkillCoefficientType as exc:
                unresolved.append(
                    f"{skill.name}: coefficient {coefficient.coefficient_number}: {exc}"
                )
                continue
            components.append(trace)

        raw_total = sum(component.final_value for component in components) if components else None
        if not components and not unresolved:
            unresolved.append(f"{skill.name}: no active coefficient components")

        return SkillTooltipResult(
            skill=skill,
            scaling=scaling,
            components=tuple(components),
            raw_total=raw_total,
            unresolved=tuple(unresolved),
        )
