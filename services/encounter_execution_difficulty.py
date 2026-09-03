from __future__ import annotations

"""Apply difficulty-specific interaction availability to Phase 10 execution results."""

from dataclasses import replace

from minmax.coverage_classification import CoverageClassification
from services.encounter_difficulty import EncounterDifficulty, normalize_encounter_difficulty
from services.encounter_execution_availability import EncounterExecutionAvailabilityService
from services.encounter_execution_evaluation import (
    EncounterExecutionEvaluation,
    EncounterExecutionEvaluator,
)
from services.encounter_service import EncounterService


class DifficultyAwareEncounterExecutionEvaluator:
    """Decorate base execution readiness with exact difficulty-specific exceptions."""

    def __init__(self, encounter_service: EncounterService) -> None:
        self._base = EncounterExecutionEvaluator(encounter_service)
        self._availability = EncounterExecutionAvailabilityService(encounter_service)

    def evaluate(
        self,
        encounter_id: str,
        difficulty: EncounterDifficulty | str = EncounterDifficulty.VETERAN,
    ) -> EncounterExecutionEvaluation:
        selected = normalize_encounter_difficulty(difficulty)
        base = self._base.evaluate(encounter_id)
        availability_rows = self._availability.rows(encounter_id, selected)
        if not availability_rows:
            return base

        by_key = {
            (row.mechanic_name, row.interaction): row
            for row in availability_rows
        }
        output = []
        for row in base.results:
            availability = by_key.get((row.mechanic_name, row.interaction))
            if availability is None or availability.available is True:
                output.append(row)
                continue
            if availability.available is False:
                output.append(
                    replace(
                        row,
                        classification=CoverageClassification.UNKNOWN,
                        requires_player_build_capability=None,
                        explanation=(
                            availability.explanation
                            or f"The {row.interaction} interaction is unavailable on {selected.value}. "
                            "No source-backed alternate handling method is established."
                        ),
                    )
                )
                continue
            output.append(
                replace(
                    row,
                    classification=(
                        CoverageClassification.CONFLICT
                        if availability.reconciliation_status == "conflicting"
                        else CoverageClassification.UNKNOWN
                    ),
                    requires_player_build_capability=None,
                    explanation=(
                        availability.explanation
                        or f"Availability of the {row.interaction} interaction is unresolved on {selected.value}."
                    ),
                )
            )

        return EncounterExecutionEvaluation(
            encounter_id=base.encounter_id,
            results=tuple(output),
        )
