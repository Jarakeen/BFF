from __future__ import annotations

"""Conservative Phase 11 assignment over canonical provider candidate sets.

The first assignment boundary chooses providers only when Phase 10 evidence leaves no
choice to arbitrate. Multiple viable providers remain an unresolved selection until
explicit suitability evidence exists. Deterministic ordering is not treated as game
mechanics, which prevents roster order from quietly becoming a fake strategy rule.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateSet,
    ProviderCandidateStatus,
)


class ProviderAssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    UNRESOLVED_SELECTION = "unresolved_selection"
    UNRESOLVED_CAPABILITY = "unresolved_capability"
    CONFLICT = "conflict"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class ProviderAssignment:
    requirement_id: str
    encounter_id: str
    requirement_type: str
    status: ProviderAssignmentStatus
    primary_providers: tuple[ProviderCandidate, ...]
    backup_providers: tuple[ProviderCandidate, ...]
    unresolved_candidates: tuple[ProviderCandidate, ...]
    conflicting_candidates: tuple[ProviderCandidate, ...]
    explanation: str

    @property
    def is_assigned(self) -> bool:
        return self.status == ProviderAssignmentStatus.ASSIGNED


class EncounterProviderAssignmentService:
    """Make only assignments uniquely determined by current explicit evidence."""

    def assign(
        self,
        candidate_sets: tuple[ProviderCandidateSet, ...],
    ) -> tuple[ProviderAssignment, ...]:
        return tuple(self._assign_one(candidate_set) for candidate_set in candidate_sets)

    @staticmethod
    def _assign_one(candidate_set: ProviderCandidateSet) -> ProviderAssignment:
        viable = candidate_set.viable
        unresolved = candidate_set.unresolved
        conflicting = candidate_set.conflicting
        required = candidate_set.required_provider_count

        if conflicting:
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.CONFLICT,
                primary_providers=(),
                backup_providers=viable,
                unresolved_candidates=unresolved,
                conflicting_candidates=conflicting,
                explanation=(
                    "Phase 10 contains conflicting provider evidence; Phase 11 cannot "
                    "choose a provider until that conflict is resolved."
                ),
            )

        if len(viable) < required:
            if unresolved:
                return ProviderAssignment(
                    requirement_id=candidate_set.requirement_id,
                    encounter_id=candidate_set.encounter_id,
                    requirement_type=candidate_set.requirement_type,
                    status=ProviderAssignmentStatus.UNRESOLVED_CAPABILITY,
                    primary_providers=(),
                    backup_providers=viable,
                    unresolved_candidates=unresolved,
                    conflicting_candidates=(),
                    explanation=(
                        f"Only {len(viable)} proven provider(s) are available for "
                        f"{required} required provider(s), and unresolved candidates "
                        "could still change the assignment."
                    ),
                )
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.INSUFFICIENT,
                primary_providers=(),
                backup_providers=viable,
                unresolved_candidates=(),
                conflicting_candidates=(),
                explanation=(
                    f"Only {len(viable)} proven provider(s) are available for "
                    f"{required} required provider(s)."
                ),
            )

        if len(viable) == required:
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.ASSIGNED,
                primary_providers=viable,
                backup_providers=(),
                unresolved_candidates=unresolved,
                conflicting_candidates=(),
                explanation=(
                    "Every proven viable provider is required, so the assignment is "
                    "uniquely determined without a strategy preference."
                ),
            )

        # More viable providers exist than the requirement needs. Choosing the first
        # by tuple or roster order would be deterministic but not evidence-based.
        return ProviderAssignment(
            requirement_id=candidate_set.requirement_id,
            encounter_id=candidate_set.encounter_id,
            requirement_type=candidate_set.requirement_type,
            status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
            primary_providers=(),
            backup_providers=viable,
            unresolved_candidates=unresolved,
            conflicting_candidates=(),
            explanation=(
                f"{len(viable)} viable providers satisfy a requirement for {required}; "
                "explicit suitability evidence is required before choosing primary "
                "provider(s). Roster order is not treated as a strategy rule."
            ),
        )
