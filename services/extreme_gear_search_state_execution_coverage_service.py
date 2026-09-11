from __future__ import annotations

"""Prove that every reviewed Extreme gear search-state rule has an execution owner.

The relevance layer may recognize mechanics that mutate the legal search space, but
recognition is not execution. This audit deliberately keeps the reviewed rule enum
and the concrete execution surfaces paired so a newly-added rule cannot silently
remain accounting-only.
"""

from dataclasses import dataclass

from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule


@dataclass(frozen=True)
class ExtremeGearSearchStateExecutionCoverage:
    rule: ExtremeGearSearchStateRule
    execution_surfaces: tuple[str, ...]
    notes: str = ""

    @property
    def executable(self) -> bool:
        return bool(self.execution_surfaces)


@dataclass(frozen=True)
class ExtremeGearSearchStateExecutionCoverageReport:
    rows: tuple[ExtremeGearSearchStateExecutionCoverage, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        expected = set(ExtremeGearSearchStateRule)
        observed = {row.rule for row in self.rows if row.executable}
        return observed == expected and not self.unresolved


class ExtremeGearSearchStateExecutionCoverageService:
    """Return reviewed execution ownership for every search-state rule."""

    _EXECUTION_SURFACES: dict[ExtremeGearSearchStateRule, tuple[str, ...]] = {
        ExtremeGearSearchStateRule.ONE_BAR_ONLY: (
            "services.extreme_gear_bar_access_service.ExtremeGearBarAccessService",
            "services.rotation_saved_build_bar_access_service.RotationSavedBuildBarAccessService",
            "services.rotation_runtime_bar_provenance_service.RotationRuntimeBarProvenanceService",
        ),
        ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES: (
            "minmax.gear_set_effect_service.GearSetEffectService",
        ),
        ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS: (
            "services.extreme_twice_born_mundus_structural_stat_evaluator.ExtremeTwiceBornMundusStructuralStatEvaluator",
            "services.extreme_best_named_gear_resource_armor_mundus_food_potion_structural_stat_evaluator.ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory",
        ),
    }

    _NOTES: dict[ExtremeGearSearchStateRule, str] = {
        ExtremeGearSearchStateRule.ONE_BAR_ONLY: (
            "Oakensoul preserves physical backup equipment but only the front bar may become active; rotation and runtime BAR_SWAP paths fail closed."
        ),
        ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES: (
            "Torc preserves equipped pieces, traits, glyphs, and non-set inputs while canonical item-set effect activation suppresses every other set bonus."
        ),
        ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS: (
            "Twice-Born Star expands the finite Mundus search to zero, one, or two distinct boons and reuses canonical build scoring."
        ),
    }

    @classmethod
    def build(cls) -> ExtremeGearSearchStateExecutionCoverageReport:
        rows: list[ExtremeGearSearchStateExecutionCoverage] = []
        unresolved: list[str] = []
        for rule in ExtremeGearSearchStateRule:
            surfaces = tuple(cls._EXECUTION_SURFACES.get(rule, ()))
            if not surfaces:
                unresolved.append(
                    f"Extreme gear search-state rule has no reviewed execution surface: {rule.value}"
                )
            rows.append(
                ExtremeGearSearchStateExecutionCoverage(
                    rule=rule,
                    execution_surfaces=surfaces,
                    notes=cls._NOTES.get(rule, ""),
                )
            )

        stale = set(cls._EXECUTION_SURFACES) - set(ExtremeGearSearchStateRule)
        for rule in sorted(stale, key=lambda value: str(value)):
            unresolved.append(f"stale Extreme gear search-state execution mapping: {rule}")

        return ExtremeGearSearchStateExecutionCoverageReport(
            rows=tuple(rows),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeGearSearchStateExecutionCoverage",
    "ExtremeGearSearchStateExecutionCoverageReport",
    "ExtremeGearSearchStateExecutionCoverageService",
]
