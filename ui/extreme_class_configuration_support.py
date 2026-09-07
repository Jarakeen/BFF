from __future__ import annotations

from dataclasses import replace

from services.extreme_class_configuration_service import ExtremeClassConfigurationService

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
        notes = tuple(result.notes) + (
            f"Class legality catalog contains {candidate_count:,} legal pure/subclass configurations across all seven base classes.",
            "Pure-class candidates may use Class Mastery; subclass candidates may not. Class Mastery effects are not scored until their canonical passive effects are resolved, so BFF will not claim a pure/subclass winner prematurely.",
            "Objective checklist: " + "; ".join(checklist) + ".",
        )
        return replace(result, notes=notes)

    ExtremeBlueprintService.optimize_from_scratch = optimize_with_legality_checklist
    _INSTALLED = True
