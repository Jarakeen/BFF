from __future__ import annotations

"""Read-only corpus audit for Phase 10 cleanse-method coverage."""

from dataclasses import dataclass

from services.encounter_cleanse_method import (
    CleanseMethod,
    CleanseMethodResolution,
    EncounterCleanseMethodService,
)
from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterCleanseMethodAuditRow:
    encounter_id: str
    cleanse_requirement_count: int
    resolved_method_count: int
    unresolved_method_count: int
    conflicting_method_count: int
    encounter_interaction_count: int
    core_action_count: int
    player_build_method_count: int

    @property
    def has_cleanse_requirement(self) -> bool:
        return self.cleanse_requirement_count > 0

    @property
    def has_method_coverage(self) -> bool:
        return self.resolved_method_count > 0


@dataclass(frozen=True)
class EncounterCleanseMethodAudit:
    rows: tuple[EncounterCleanseMethodAuditRow, ...]

    @property
    def encounters_with_cleanse_requirements(self) -> int:
        return sum(row.has_cleanse_requirement for row in self.rows)

    @property
    def encounters_with_resolved_methods(self) -> int:
        return sum(row.has_method_coverage for row in self.rows)

    @property
    def encounters_missing_method_detail(self) -> int:
        return sum(
            row.has_cleanse_requirement and not row.has_method_coverage
            for row in self.rows
        )

    @property
    def resolved_method_count(self) -> int:
        return sum(row.resolved_method_count for row in self.rows)

    @property
    def encounter_interaction_count(self) -> int:
        return sum(row.encounter_interaction_count for row in self.rows)

    @property
    def core_action_count(self) -> int:
        return sum(row.core_action_count for row in self.rows)

    @property
    def player_build_method_count(self) -> int:
        return sum(row.player_build_method_count for row in self.rows)


def audit_encounter_cleanse_methods(service: EncounterService) -> EncounterCleanseMethodAudit:
    method_service = EncounterCleanseMethodService(service)
    rows: list[EncounterCleanseMethodAuditRow] = []

    for encounter_id in service.encounter_ids():
        requirements = tuple(
            requirement
            for requirement in service.requirements(encounter_id)
            if requirement.requirement_type == "cleanse"
        )
        methods = method_service.methods(encounter_id)
        resolved = tuple(
            method
            for method in methods
            if method.resolution == CleanseMethodResolution.RESOLVED
        )
        rows.append(
            EncounterCleanseMethodAuditRow(
                encounter_id=encounter_id,
                cleanse_requirement_count=len(requirements),
                resolved_method_count=len(resolved),
                unresolved_method_count=sum(
                    method.resolution == CleanseMethodResolution.UNRESOLVED
                    for method in methods
                ),
                conflicting_method_count=sum(
                    method.resolution == CleanseMethodResolution.CONFLICTING
                    for method in methods
                ),
                encounter_interaction_count=sum(
                    method.method == CleanseMethod.ENCOUNTER_INTERACTION
                    for method in resolved
                ),
                core_action_count=sum(
                    method.method == CleanseMethod.CORE_ACTION
                    for method in resolved
                ),
                player_build_method_count=sum(
                    method.method in {CleanseMethod.SELF_SKILL, CleanseMethod.GROUP_SKILL}
                    for method in resolved
                ),
            )
        )

    return EncounterCleanseMethodAudit(tuple(rows))
