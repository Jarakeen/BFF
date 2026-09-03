from __future__ import annotations

"""Explicit Phase 11 double-duty conflict evidence for provider assignments.

A player is not considered overcommitted merely because they appear on more than one
provider row. That would turn proximity in a report into invented strategy. This
module reports double-duty conflicts only when source-backed evidence explicitly says
that one member cannot carry two exact encounter requirements together.
"""

from dataclasses import dataclass

from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)


@dataclass(frozen=True)
class ProviderResponsibilityConflictEvidence:
    """Proof that one member cannot own two exact requirements simultaneously."""

    encounter_id: str
    member_id: str
    first_requirement_id: str
    second_requirement_id: str
    source: str
    explanation: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "encounter_id",
            "member_id",
            "first_requirement_id",
            "second_requirement_id",
            "source",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must be non-empty")
        if self.first_requirement_id == self.second_requirement_id:
            raise ValueError("responsibility conflict must reference two distinct requirements")

    @property
    def requirement_pair(self) -> tuple[str, str]:
        return tuple(sorted((self.first_requirement_id, self.second_requirement_id)))


@dataclass(frozen=True)
class ProviderResponsibilityConflict:
    encounter_id: str
    member_id: str
    requirement_ids: tuple[str, str]
    evidence: tuple[ProviderResponsibilityConflictEvidence, ...]


@dataclass(frozen=True)
class ProviderResponsibilityAudit:
    conflicts: tuple[ProviderResponsibilityConflict, ...]

    @property
    def is_conflict_free(self) -> bool:
        return not self.conflicts


class EncounterProviderResponsibilityService:
    """Audit primary assignments against explicit double-duty restrictions."""

    def audit(
        self,
        assignments: tuple[ProviderAssignment, ...],
        evidence: tuple[ProviderResponsibilityConflictEvidence, ...] = (),
    ) -> ProviderResponsibilityAudit:
        assignments_by_requirement: dict[str, ProviderAssignment] = {}
        for assignment in assignments:
            if assignment.requirement_id in assignments_by_requirement:
                raise ValueError("assignments cannot duplicate requirement_id")
            assignments_by_requirement[assignment.requirement_id] = assignment

        evidence_by_key: dict[
            tuple[str, str, tuple[str, str]],
            list[ProviderResponsibilityConflictEvidence],
        ] = {}
        for row in evidence:
            first = assignments_by_requirement.get(row.first_requirement_id)
            second = assignments_by_requirement.get(row.second_requirement_id)
            if first is None or second is None:
                raise ValueError(
                    "responsibility conflict evidence references a requirement without an assignment"
                )
            if first.encounter_id != row.encounter_id or second.encounter_id != row.encounter_id:
                raise ValueError(
                    "responsibility conflict evidence encounter_id does not match assignments"
                )
            key = (row.encounter_id, row.member_id, row.requirement_pair)
            evidence_by_key.setdefault(key, []).append(row)

        conflicts: list[ProviderResponsibilityConflict] = []
        for (encounter_id, member_id, requirement_pair), rows in evidence_by_key.items():
            first = assignments_by_requirement[requirement_pair[0]]
            second = assignments_by_requirement[requirement_pair[1]]
            if first.status != ProviderAssignmentStatus.ASSIGNED:
                continue
            if second.status != ProviderAssignmentStatus.ASSIGNED:
                continue
            first_members = {candidate.member_id for candidate in first.primary_providers}
            second_members = {candidate.member_id for candidate in second.primary_providers}
            if member_id not in first_members or member_id not in second_members:
                continue
            conflicts.append(
                ProviderResponsibilityConflict(
                    encounter_id=encounter_id,
                    member_id=member_id,
                    requirement_ids=requirement_pair,
                    evidence=tuple(rows),
                )
            )

        return ProviderResponsibilityAudit(conflicts=tuple(conflicts))
