from __future__ import annotations

from dataclasses import dataclass

from .build_calculation_context import BuildCalculationContext
from .skill_coefficient_repository import ResolvedSkillRank, SkillCoefficientRepository
from .skill_coefficients import (
    InactiveSkillCoefficientTrace,
    SkillCoefficientTrace,
    SkillScalingInputs,
    UnsupportedSkillCoefficientType,
    evaluate_skill_coefficient,
    is_inactive_skill_coefficient,
)
from .skill_component_actual_effect_modifiers import (
    SkillComponentActualEffectModifier,
    SkillComponentActualEffectTrace,
)
from .skill_effect_modifiers import (
    SkillEffectModifier,
    SkillEffectModifierTrace,
    apply_skill_effect_modifier,
)
from .skill_tooltip_rounding import (
    SkillTooltipRoundingCandidates,
    tooltip_rounding_candidates,
)
from .stat_ids import StatId


@dataclass(frozen=True)
class SkillTooltipResult:
    skill: ResolvedSkillRank | None
    scaling: SkillScalingInputs | None
    components: tuple[SkillCoefficientTrace, ...]
    inactive_components: tuple[InactiveSkillCoefficientTrace, ...]
    raw_total: float | None
    tooltip_value: float | None
    actual_effect_value: float | None
    tooltip_modifier_trace: tuple[SkillEffectModifierTrace, ...]
    actual_effect_modifier_trace: tuple[SkillEffectModifierTrace, ...]
    rounding_candidates: SkillTooltipRoundingCandidates | None
    component_actual_effect_trace: tuple[SkillComponentActualEffectTrace, ...] = ()
    unresolved: tuple[str, ...] = ()


class SkillTooltipCalculator:
    """Phase 3 skill-value pipeline.

    The calculator deliberately keeps three layers separate::

        raw coefficient value
            -> verified tooltip-visible modifiers
            -> displayed-tooltip candidate
            -> verified per-component actual-effect-only modifiers
            -> verified whole-effect actual-only/additional modifiers
            -> actual-effect candidate

    Per-component actual modifiers can change a coefficient's power input and/or
    its own additive percentage bucket without leaking that change into other
    components on a mixed ability. They never alter the tooltip candidate.
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

    def evaluate_entity_id(
        self,
        entity_id: str,
        context: BuildCalculationContext,
        *,
        modifiers: tuple[SkillEffectModifier, ...] = (),
        component_actual_effect_modifiers: tuple[SkillComponentActualEffectModifier, ...] = (),
    ) -> SkillTooltipResult:
        resolution = self.repository.resolve_entity_id(entity_id)
        if resolution.rank is None:
            return self._unresolved_result(resolution.unresolved)
        return self._evaluate_resolution(
            resolution.rank,
            resolution.unresolved,
            context,
            modifiers,
            component_actual_effect_modifiers,
        )

    def evaluate_name(
        self,
        name: str,
        context: BuildCalculationContext,
        *,
        modifiers: tuple[SkillEffectModifier, ...] = (),
        component_actual_effect_modifiers: tuple[SkillComponentActualEffectModifier, ...] = (),
    ) -> SkillTooltipResult:
        resolution = self.repository.resolve_name(name)
        if resolution.rank is None:
            return self._unresolved_result(resolution.unresolved)
        return self._evaluate_resolution(
            resolution.rank,
            resolution.unresolved,
            context,
            modifiers,
            component_actual_effect_modifiers,
        )

    def evaluate_ability_id(
        self,
        ability_id: int,
        context: BuildCalculationContext,
        *,
        modifiers: tuple[SkillEffectModifier, ...] = (),
        component_actual_effect_modifiers: tuple[SkillComponentActualEffectModifier, ...] = (),
    ) -> SkillTooltipResult:
        """Source/crosswalk lookup retained for diagnostics and reconciliation."""

        resolution = self.repository.resolve_ability_id(ability_id)
        if resolution.rank is None:
            return self._unresolved_result(resolution.unresolved)
        return self._evaluate_resolution(
            resolution.rank,
            resolution.unresolved,
            context,
            modifiers,
            component_actual_effect_modifiers,
        )

    @staticmethod
    def _unresolved_result(unresolved: tuple[str, ...]) -> SkillTooltipResult:
        return SkillTooltipResult(
            skill=None,
            scaling=None,
            components=(),
            inactive_components=(),
            raw_total=None,
            tooltip_value=None,
            actual_effect_value=None,
            tooltip_modifier_trace=(),
            actual_effect_modifier_trace=(),
            rounding_candidates=None,
            unresolved=unresolved,
        )

    @staticmethod
    def _component_modifier_map(
        modifiers: tuple[SkillComponentActualEffectModifier, ...],
    ) -> tuple[dict[int, SkillComponentActualEffectModifier], tuple[str, ...]]:
        result: dict[int, SkillComponentActualEffectModifier] = {}
        unresolved: list[str] = []
        for modifier in modifiers:
            key = int(modifier.coefficient_number)
            if key in result:
                unresolved.append(
                    f"Duplicate actual-effect component modifier for coefficient {key}"
                )
                continue
            result[key] = modifier
        return result, tuple(unresolved)

    def _evaluate_resolution(
        self,
        skill: ResolvedSkillRank,
        unresolved_seed: tuple[str, ...],
        context: BuildCalculationContext,
        modifiers: tuple[SkillEffectModifier, ...],
        component_actual_effect_modifiers: tuple[SkillComponentActualEffectModifier, ...],
    ) -> SkillTooltipResult:
        unresolved = list(unresolved_seed)
        scaling = self.scaling_from_context(context)
        components: list[SkillCoefficientTrace] = []
        inactive_components: list[InactiveSkillCoefficientTrace] = []
        component_actual_trace: list[SkillComponentActualEffectTrace] = []
        actual_component_values: list[float] = []
        component_modifier_map, duplicate_errors = self._component_modifier_map(
            component_actual_effect_modifiers
        )
        unresolved.extend(duplicate_errors)

        for coefficient in skill.coefficients:
            coefficient_type = str(coefficient.type or "").strip()
            if is_inactive_skill_coefficient(coefficient):
                inactive_components.append(
                    InactiveSkillCoefficientTrace(
                        coefficient_number=coefficient.coefficient_number,
                        coefficient_type=coefficient_type,
                        a=coefficient.a,
                        b=coefficient.b,
                        c=coefficient.c,
                        r=coefficient.r,
                        reason="source marks this coefficient slot inactive/sentinel",
                    )
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
                    f"{skill.entity_id}: coefficient {coefficient.coefficient_number}: {exc}"
                )
                continue
            components.append(trace)

            component_modifier = component_modifier_map.pop(
                int(coefficient.coefficient_number), None
            )
            if component_modifier is None:
                actual_component_values.append(trace.final_value)
                continue

            effective_power = scaling.highest_offensive_power + float(
                component_modifier.power_bonus
            )
            try:
                actual_coefficient = evaluate_skill_coefficient(
                    coefficient,
                    max_stat=scaling.highest_max_resource,
                    power=effective_power,
                )
            except UnsupportedSkillCoefficientType as exc:
                unresolved.append(
                    f"{skill.entity_id}: coefficient {coefficient.coefficient_number} actual-effect modifier: {exc}"
                )
                actual_component_values.append(trace.final_value)
                continue

            output_value = actual_coefficient.final_value * (
                1.0 + float(component_modifier.additive_percent) / 100.0
            )
            actual_component_values.append(output_value)
            component_actual_trace.append(
                SkillComponentActualEffectTrace(
                    coefficient_number=int(coefficient.coefficient_number),
                    base_power=scaling.highest_offensive_power,
                    power_bonus=float(component_modifier.power_bonus),
                    effective_power=effective_power,
                    coefficient_value=actual_coefficient.final_value,
                    additive_percent=float(component_modifier.additive_percent),
                    output_value=output_value,
                    sources=tuple(component_modifier.sources),
                )
            )

        for missing_number in sorted(component_modifier_map):
            unresolved.append(
                f"{skill.entity_id}: actual-effect modifier targets missing/inactive coefficient {missing_number}"
            )

        raw_total = sum(component.final_value for component in components) if components else None
        if not components and not unresolved and not inactive_components:
            unresolved.append(f"{skill.entity_id}: no active coefficient components")

        tooltip_value = raw_total
        actual_effect_value = (
            sum(actual_component_values) if actual_component_values else raw_total
        )
        tooltip_trace: list[SkillEffectModifierTrace] = []
        actual_trace: list[SkillEffectModifierTrace] = []

        if raw_total is not None:
            for modifier in modifiers:
                if modifier.affects_tooltip:
                    trace = apply_skill_effect_modifier(tooltip_value, modifier)
                    tooltip_trace.append(trace)
                    tooltip_value = trace.output_value
                if modifier.affects_actual_effect and actual_effect_value is not None:
                    trace = apply_skill_effect_modifier(actual_effect_value, modifier)
                    actual_trace.append(trace)
                    actual_effect_value = trace.output_value

        rounding = (
            tooltip_rounding_candidates(tooltip_value)
            if tooltip_value is not None
            else None
        )

        return SkillTooltipResult(
            skill=skill,
            scaling=scaling,
            components=tuple(components),
            inactive_components=tuple(inactive_components),
            raw_total=raw_total,
            tooltip_value=tooltip_value,
            actual_effect_value=actual_effect_value,
            tooltip_modifier_trace=tuple(tooltip_trace),
            actual_effect_modifier_trace=tuple(actual_trace),
            rounding_candidates=rounding,
            component_actual_effect_trace=tuple(component_actual_trace),
            unresolved=tuple(unresolved),
        )
