from __future__ import annotations

"""Read-only Phase 10 audit of execution-readiness classifications."""

from dataclasses import dataclass

from minmax.coverage_classification import CoverageClassification
from services.encounter_execution_evaluation import EncounterExecutionEvaluator
from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterExecutionAuditRow:
    encounter_id: str
    requirement_count: int
    covered_count: int
    unknown_count: int
    conflict_count: int

    @property
    def has_requirements(self) -> bool:
        return self.requirement_count > 0

    @property
    def fully_evaluable(self) -> bool:
        return self.has_requirements and self.unknown_count == 0

    @property
    def fully_ready(self) -> bool:
        return self.fully_evaluable and self.conflict_count == 0


@dataclass(frozen=True)
class EncounterExecutionAudit:
    rows: tuple[EncounterExecutionAuditRow, ...]

    @property
    def encounters_with_requirements(self) -> int:
        return sum(row.has_requirements for row in self.rows)

    @property
    def fully_evaluable_encounters(self) -> int:
        return sum(row.fully_evaluable for row in self.rows)

    @property
    def fully_ready_encounters(self) -> int:
        return sum(row.fully_ready for row in self.rows)

    @property
    def covered_requirement_count(self) -> int:
        return sum(row.covered_count for row in self.rows)

    @property
    def unknown_requirement_count(self) -> int:
        return sum(row.unknown_count for row in self.rows)

    @property
    def conflict_requirement_count(self) -> int:
        return sum(row.conflict_count for row in self.rows)


def audit_encounter_execution(service: EncounterService) -> EncounterExecutionAudit:
    evaluator = EncounterExecutionEvaluator(service)
    rows: list[EncounterExecutionAuditRow] = []
    for encounter_id in service.encounter_ids():
        evaluation = evaluator.evaluate(encounter_id)
        rows.append(
            EncounterExecutionAuditRow(
                encounter_id=encounter_id,
                requirement_count=len(evaluation.results),
                covered_count=sum(
                    row.classification == CoverageClassification.COVERED
                    for row in evaluation.results
                ),
                unknown_count=sum(
                    row.classification == CoverageClassification.UNKNOWN
                    for row in evaluation.results
                ),
                conflict_count=sum(
                    row.classification == CoverageClassification.CONFLICT
                    for row in evaluation.results
                ),
            )
        )
    return EncounterExecutionAudit(tuple(rows))
