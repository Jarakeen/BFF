from __future__ import annotations

"""Read-only corpus audit for Phase 10 interrupt-method coverage."""

from dataclasses import dataclass

from services.encounter_interrupt_method import (
    InterruptMethod,
    InterruptMethodResolution,
    EncounterInterruptMethodService,
)
from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterInterruptMethodAuditRow:
    encounter_id: str
    interrupt_requirement_count: int
    resolved_method_count: int
    unresolved_method_count: int
    conflicting_method_count: int
    core_bash_count: int
    player_skill_count: int
    encounter_interaction_count: int
    ranged_required_count: int

    @property
    def has_interrupt_requirement(self) -> bool:
        return self.interrupt_requirement_count > 0

    @property
    def has_method_coverage(self) -> bool:
        return self.resolved_method_count > 0


@dataclass(frozen=True)
class EncounterInterruptMethodAudit:
    rows: tuple[EncounterInterruptMethodAuditRow, ...]

    @property
    def encounters_with_interrupt_requirements(self) -> int:
        return sum(row.has_interrupt_requirement for row in self.rows)

    @property
    def encounters_with_resolved_methods(self) -> int:
        return sum(row.has_method_coverage for row in self.rows)

    @property
    def encounters_missing_method_detail(self) -> int:
        return sum(
            row.has_interrupt_requirement and not row.has_method_coverage
            for row in self.rows
        )

    @property
    def resolved_method_count(self) -> int:
        return sum(row.resolved_method_count for row in self.rows)

    @property
    def core_bash_count(self) -> int:
        return sum(row.core_bash_count for row in self.rows)

    @property
    def player_skill_count(self) -> int:
        return sum(row.player_skill_count for row in self.rows)

    @property
    def encounter_interaction_count(self) -> int:
        return sum(row.encounter_interaction_count for row in self.rows)

    @property
    def ranged_required_count(self) -> int:
        return sum(row.ranged_required_count for row in self.rows)


def audit_encounter_interrupt_methods(service: EncounterService) -> EncounterInterruptMethodAudit:
    method_service = EncounterInterruptMethodService(service)
    rows: list[EncounterInterruptMethodAuditRow] = []

    for encounter_id in service.encounter_ids():
        requirements = tuple(
            requirement
            for requirement in service.requirements(encounter_id)
            if requirement.requirement_type == "interrupt"
        )
        methods = method_service.methods(encounter_id)
        resolved = tuple(
            method
            for method in methods
            if method.resolution == InterruptMethodResolution.RESOLVED
        )
        rows.append(
            EncounterInterruptMethodAuditRow(
                encounter_id=encounter_id,
                interrupt_requirement_count=len(requirements),
                resolved_method_count=len(resolved),
                unresolved_method_count=sum(
                    method.resolution == InterruptMethodResolution.UNRESOLVED
                    for method in methods
                ),
                conflicting_method_count=sum(
                    method.resolution == InterruptMethodResolution.CONFLICTING
                    for method in methods
                ),
                core_bash_count=sum(
                    method.method == InterruptMethod.CORE_BASH for method in resolved
                ),
                player_skill_count=sum(
                    method.method == InterruptMethod.PLAYER_SKILL for method in resolved
                ),
                encounter_interaction_count=sum(
                    method.method == InterruptMethod.ENCOUNTER_INTERACTION
                    for method in resolved
                ),
                ranged_required_count=sum(
                    method.ranged_required is True for method in resolved
                ),
            )
        )

    return EncounterInterruptMethodAudit(tuple(rows))
