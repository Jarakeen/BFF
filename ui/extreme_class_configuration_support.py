from __future__ import annotations

from dataclasses import replace

from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_class_route_comparison_service import ExtremeClassRouteComparisonService

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from services.extreme_blueprint_service import ExtremeBlueprintService

    original_optimize = ExtremeBlueprintService.optimize_from_scratch

    def optimize_with_legality_checklist(self, objective_key, *, active_bar="front", max_passes=24):
        result = original_optimize(
            self,
            objective_key,
            active_bar=active_bar,
            max_passes=max_passes,
        )
        candidate_count = len(ExtremeClassConfigurationService.all_candidates())
        checklist = ExtremeClassConfigurationService.objective_checklist()
        comparison = ExtremeClassRouteComparisonService(self.database_path).compare(
            result.objective.key,
            reference_value=result.resting_value,
        )

        route_note = (
            f"Reviewed pure-class Class Mastery scoring currently has no numeric route for {result.objective.label}."
        )
        best = comparison.best_reviewed_pure_route
        if best is not None:
            mastery_text = " + ".join(best.mastery_names) or "no reviewed mastery"
            route_note = (
                f"Best currently reviewed pure-class mastery route for {result.objective.label}: "
                f"{best.base_class.value.title()} with {mastery_text}; projected mastery-only delta "
                f"{best.projected_delta:g} under {best.boundary.value if best.boundary else 'unresolved'} conditions."
            )

        notes = tuple(result.notes) + (
            f"Class legality catalog contains {candidate_count:,} legal pure/subclass configurations across all seven base classes.",
            route_note,
            f"{comparison.unresolved_subclass_count:,} legal subclass configurations are still pending objective-specific borrowed-line effect scoring, so BFF does not promote the reviewed pure route to a global class winner.",
            "Pure-class candidates may use up to two Class Mastery passives; subclass candidates may not use Class Mastery.",
            "Objective checklist: " + "; ".join(checklist) + ".",
        )
        return replace(result, notes=notes)

    ExtremeBlueprintService.optimize_from_scratch = optimize_with_legality_checklist
    _INSTALLED = True
