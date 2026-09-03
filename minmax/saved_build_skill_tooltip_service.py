from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from models.build_model import PlayerBuild

from .build_calculation_context import BuildCalculationContext
from .healing_champion_point_component_resolver import (
    HealingChampionPointComponentResolver,
)
from .saved_build_champion_point_slots import adapt_saved_champion_point_slots
from .skill_coefficient_repository import SkillCoefficientRepository
from .skill_component_actual_effect_modifiers import SkillComponentActualEffectModifier
from .skill_component_classification import SkillEffectKind
from .skill_component_repository import SkillComponentRepository
from .skill_tooltip_calculator import SkillTooltipCalculator, SkillTooltipResult
from .stat_ids import StatId


class SavedBuildSkillTooltipService:
    """Evaluate one saved-build skill through canonical component-level math.

    The service owns saved-build orchestration only. Champion Point mechanics
    stay in ``HealingChampionPointComponentResolver`` and coefficient math stays
    in ``SkillTooltipCalculator``.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        coefficient_repository: SkillCoefficientRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
        healing_cp_resolver: HealingChampionPointComponentResolver | None = None,
        calculator: SkillTooltipCalculator | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.coefficients = coefficient_repository or SkillCoefficientRepository(database_path)
        self.components = component_repository or SkillComponentRepository(database_path)
        self.healing_cp = healing_cp_resolver or HealingChampionPointComponentResolver(database_path)
        self.calculator = calculator or SkillTooltipCalculator(self.coefficients)

    @staticmethod
    def _sheet_healing_done_percent(context: BuildCalculationContext) -> float:
        """Return canonical sheet Healing Done as the component percent bucket.

        ``CoreStatState`` stores ratio-like combat stats as decimal ratios, so a
        sheet value of 8% is represented as ``0.08`` and becomes ``8.0`` here.
        Missing legacy context state remains neutral rather than inventing a
        modifier; production skill evaluation still requires core state in the
        coefficient calculator itself.
        """

        core_state = getattr(context, "core_state", None)
        if core_state is None:
            return 0.0
        trace = core_state.derived.get(StatId.HEALING_DONE)
        if trace is None:
            return 0.0
        return float(trace.final_value) * 100.0

    @classmethod
    def _combine_healing_modifiers(
        cls,
        *,
        context: BuildCalculationContext,
        heal_coefficients: tuple[int, ...],
        cp_modifiers: tuple[SkillComponentActualEffectModifier, ...],
    ) -> tuple[SkillComponentActualEffectModifier, ...]:
        """Combine sheet Healing Done with verified per-component healing CP.

        Both inputs belong to the same additive Healing Done category at actual
        effect scope. Critical Healing is deliberately not included because a
        normal heal value is not a critical-hit expected-value model.
        """

        sheet_healing_done = cls._sheet_healing_done_percent(context)
        by_coefficient = {
            int(modifier.coefficient_number): modifier
            for modifier in cp_modifiers
        }
        result: list[SkillComponentActualEffectModifier] = []
        for coefficient_number in heal_coefficients:
            cp = by_coefficient.get(int(coefficient_number))
            power_bonus = float(cp.power_bonus) if cp is not None else 0.0
            additive_percent = float(cp.additive_percent) if cp is not None else 0.0
            sources = tuple(cp.sources) if cp is not None else ()
            if sheet_healing_done:
                additive_percent += sheet_healing_done
                sources = sources + ("Character sheet: Healing Done",)
            if power_bonus or additive_percent or sources:
                result.append(
                    SkillComponentActualEffectModifier(
                        coefficient_number=int(coefficient_number),
                        power_bonus=power_bonus,
                        additive_percent=additive_percent,
                        sources=sources,
                    )
                )
        return tuple(result)

    def evaluate_entity_id(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        entity_id: str,
    ) -> SkillTooltipResult:
        resolution = self.coefficients.resolve_entity_id(entity_id)
        if resolution.rank is None:
            return self.calculator.evaluate_entity_id(entity_id, context)

        slot_adaptation = adapt_saved_champion_point_slots(build)
        heal_coefficients = tuple(
            component.coefficient_number
            for component in self.components.get_for_skill_rank(
                resolution.rank.skill_rank_id
            )
            if component.effect_kind is SkillEffectKind.HEAL
        )

        cp_modifiers: tuple[SkillComponentActualEffectModifier, ...] = ()
        cp_unresolved: tuple[str, ...] = ()
        if heal_coefficients and slot_adaptation.allocations:
            cp_modifiers, cp_unresolved = self.healing_cp.resolve_for_skill(
                allocations=slot_adaptation.allocations,
                skill_rank_id=resolution.rank.skill_rank_id,
                coefficient_numbers=heal_coefficients,
                # PlayerBuild.ChampionPoints is the saved twelve-slot CP grid.
                is_slotted=True,
            )

        component_modifiers = self._combine_healing_modifiers(
            context=context,
            heal_coefficients=heal_coefficients,
            cp_modifiers=cp_modifiers,
        )
        result = self.calculator.evaluate_entity_id(
            entity_id,
            context,
            component_actual_effect_modifiers=component_modifiers,
        )
        extra_unresolved = tuple(slot_adaptation.unresolved) + tuple(cp_unresolved)
        if not extra_unresolved:
            return result
        return replace(
            result,
            unresolved=tuple(result.unresolved) + extra_unresolved,
        )