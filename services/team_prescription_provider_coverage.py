from __future__ import annotations

from dataclasses import dataclass

from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.team_prescription import PrescribedRoster


@dataclass(frozen=True)
class ProviderCoveragePrescriptionResult:
    """Auditable provider-coverage projection over one prescribed roster.

    This layer does not choose classes, gear, skills, or providers. Phase 11
    assignments remain authoritative. It only records which requirements are
    already backed by known roster anchors and which requirements must remain
    hard constraints for later prescription/candidate generation.
    """

    roster: PrescribedRoster
    satisfied_requirement_ids: tuple[str, ...]
    unresolved_requirement_ids: tuple[str, ...]


def _anchor_names(roster: PrescribedRoster) -> set[str]:
    return {
        assignment.player_name.casefold()
        for assignment in roster.assignments
        if assignment.player_name
    }


def project_provider_coverage_into_prescription(
    *,
    roster: PrescribedRoster,
    provider_assignments: tuple[ProviderAssignment, ...],
) -> ProviderCoveragePrescriptionResult:
    """Carry Phase 11 provider evidence into a non-destructive roster prescription.

    Assigned requirements are only considered satisfied when every primary
    provider resolves to a known player anchor already present in the
    prescription. Unresolved, conflicting, insufficient, or externally-referenced
    assignments stay explicit so later class/build generation cannot optimize
    damage while silently dropping required support coverage.
    """

    seen_requirement_ids: set[str] = set()
    anchors = _anchor_names(roster)
    assumptions = list(roster.assumptions)
    unresolved = list(roster.unresolved)
    satisfied_ids: list[str] = []
    unresolved_ids: list[str] = []

    for assignment in provider_assignments:
        if assignment.requirement_id in seen_requirement_ids:
            raise ValueError("provider assignments cannot duplicate requirement_id")
        seen_requirement_ids.add(assignment.requirement_id)

        if assignment.status == ProviderAssignmentStatus.ASSIGNED:
            missing_anchors = tuple(
                provider
                for provider in assignment.primary_providers
                if provider.character_name.casefold() not in anchors
            )
            if missing_anchors:
                names = ", ".join(provider.character_name for provider in missing_anchors)
                unresolved.append(
                    f"{assignment.requirement_id}: assigned provider(s) {names} are not "
                    "present as saved-player anchors in this prescribed roster"
                )
                unresolved_ids.append(assignment.requirement_id)
                continue

            providers = ", ".join(
                provider.character_name for provider in assignment.primary_providers
            )
            assumptions.append(
                f"{assignment.requirement_id}: provider requirement "
                f"{assignment.requirement_type} is assigned to {providers} by Phase 11 evidence"
            )
            satisfied_ids.append(assignment.requirement_id)
            continue

        unresolved.append(
            f"{assignment.requirement_id}: provider requirement "
            f"{assignment.requirement_type} remains {assignment.status.value}; "
            f"{assignment.explanation}"
        )
        unresolved_ids.append(assignment.requirement_id)

    projected = PrescribedRoster(
        name=roster.name,
        goal=roster.goal,
        scope=roster.scope,
        assignments=roster.assignments,
        assumptions=tuple(assumptions),
        unresolved=tuple(unresolved),
    )
    return ProviderCoveragePrescriptionResult(
        roster=projected,
        satisfied_requirement_ids=tuple(satisfied_ids),
        unresolved_requirement_ids=tuple(unresolved_ids),
    )
