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
from .skill_component_classification import SkillEffectKind
from .skill_component_repository import SkillComponentRepository
from .skill_tooltip_calculator import SkillTooltipCalculator, SkillTooltipResult


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

        component_modifiers = ()
        cp_unresolved: tuple[str, ...] = ()
        if heal_coefficients and slot_adaptation.allocations:
            component_modifiers, cp_unresolved = self.healing_cp.resolve_for_skill(
                allocations=slot_adaptation.allocations,
                skill_rank_id=resolution.rank.skill_rank_id,
                coefficient_numbers=heal_coefficients,
                # PlayerBuild.ChampionPoints is the saved twelve-slot CP grid.
                is_slotted=True,
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
