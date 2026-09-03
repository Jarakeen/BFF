from __future__ import annotations

"""Conservative Phase 11 assignment over canonical provider candidate sets.

Phase 10 remains authoritative for provider capability. Optional Phase 11 suitability
facts may eliminate an explicitly unsuitable provider or distinguish otherwise viable
providers, but UNKNOWN suitability never becomes a silent positive. Roster order is
never treated as game mechanics or a strategy preference.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateSet
from services.encounter_provider_suitability import (
    ProviderSuitabilitySet,
    ProviderSuitabilityStatus,
)


class ProviderAssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    UNRESOLVED_SELECTION = "unresolved_selection"
    UNRESOLVED_CAPABILITY = "unresolved_capability"
    UNRESOLVED_SUITABILITY = "unresolved_suitability"
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
    unsuitable_candidates: tuple[ProviderCandidate, ...] = ()
    suitability_unresolved_candidates: tuple[ProviderCandidate, ...] = ()

    @property
    def is_assigned(self) -> bool:
        return self.status == ProviderAssignmentStatus.ASSIGNED


class EncounterProviderAssignmentService:
    """Choose providers only when explicit evidence leaves a defensible choice."""

    def assign(
        self,
        candidate_sets: tuple[ProviderCandidateSet, ...],
        suitability_sets: tuple[ProviderSuitabilitySet, ...] = (),
    ) -> tuple[ProviderAssignment, ...]:
        candidate_ids = {candidate_set.requirement_id for candidate_set in candidate_sets}
        if len(candidate_ids) != len(candidate_sets):
            raise ValueError("candidate_sets cannot duplicate requirement_id")

        suitability_by_requirement: dict[str, ProviderSuitabilitySet] = {}
        for suitability_set in suitability_sets:
            if suitability_set.requirement_id in suitability_by_requirement:
                raise ValueError("suitability_sets cannot duplicate requirement_id")
            if suitability_set.requirement_id not in candidate_ids:
                raise ValueError(
                    "suitability set references a requirement without a provider candidate set"
                )
            suitability_by_requirement[suitability_set.requirement_id] = suitability_set

        return tuple(
            self._assign_one(
                candidate_set,
                suitability_by_requirement.get(candidate_set.requirement_id),
            )
            for candidate_set in candidate_sets
        )

    def _assign_one(
        self,
        candidate_set: ProviderCandidateSet,
        suitability_set: ProviderSuitabilitySet | None,
    ) -> ProviderAssignment:
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

        if suitability_set is None:
            return self._assign_without_suitability(candidate_set)

        self._validate_suitability_set(candidate_set, suitability_set)
        status_by_member = {
            row.candidate.member_id: row.status for row in suitability_set.candidates
        }
        suitable = tuple(
            candidate
            for candidate in viable
            if status_by_member[candidate.member_id] == ProviderSuitabilityStatus.SUITABLE
        )
        unassessed = tuple(
            candidate
            for candidate in viable
            if status_by_member[candidate.member_id] == ProviderSuitabilityStatus.UNASSESSED
        )
        suitability_unresolved = tuple(
            candidate
            for candidate in viable
            if status_by_member[candidate.member_id] == ProviderSuitabilityStatus.UNRESOLVED
        )
        unsuitable = tuple(
            candidate
            for candidate in viable
            if status_by_member[candidate.member_id] == ProviderSuitabilityStatus.UNSUITABLE
        )
        available = tuple(
            candidate
            for candidate in viable
            if status_by_member[candidate.member_id]
            in (ProviderSuitabilityStatus.SUITABLE, ProviderSuitabilityStatus.UNASSESSED)
        )

        if len(available) < required:
            if suitability_unresolved:
                return ProviderAssignment(
                    requirement_id=candidate_set.requirement_id,
                    encounter_id=candidate_set.encounter_id,
                    requirement_type=candidate_set.requirement_type,
                    status=ProviderAssignmentStatus.UNRESOLVED_SUITABILITY,
                    primary_providers=(),
                    backup_providers=available,
                    unresolved_candidates=unresolved,
                    conflicting_candidates=(),
                    explanation=(
                        f"Only {len(available)} provider(s) remain usable for {required} "
                        "required provider(s), but unresolved suitability evidence could "
                        "still change the assignment."
                    ),
                    unsuitable_candidates=unsuitable,
                    suitability_unresolved_candidates=suitability_unresolved,
                )
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.INSUFFICIENT,
                primary_providers=(),
                backup_providers=available,
                unresolved_candidates=unresolved,
                conflicting_candidates=(),
                explanation=(
                    f"Explicit suitability evidence leaves only {len(available)} usable "
                    f"provider(s) for {required} required provider(s)."
                ),
                unsuitable_candidates=unsuitable,
                suitability_unresolved_candidates=suitability_unresolved,
            )

        if len(suitable) >= required:
            if len(suitable) == required:
                backups = tuple(candidate for candidate in available if candidate not in suitable)
                return ProviderAssignment(
                    requirement_id=candidate_set.requirement_id,
                    encounter_id=candidate_set.encounter_id,
                    requirement_type=candidate_set.requirement_type,
                    status=ProviderAssignmentStatus.ASSIGNED,
                    primary_providers=suitable,
                    backup_providers=backups,
                    unresolved_candidates=unresolved,
                    conflicting_candidates=(),
                    explanation=(
                        "Explicit suitability evidence identifies exactly the required "
                        "number of primary providers."
                    ),
                    unsuitable_candidates=unsuitable,
                    suitability_unresolved_candidates=suitability_unresolved,
                )
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
                primary_providers=(),
                backup_providers=available,
                unresolved_candidates=unresolved,
                conflicting_candidates=(),
                explanation=(
                    f"{len(suitable)} providers are explicitly suitable for {required} "
                    "required slot(s); no evidence-backed rule distinguishes which "
                    "suitable provider should be primary."
                ),
                unsuitable_candidates=unsuitable,
                suitability_unresolved_candidates=suitability_unresolved,
            )

        remaining_needed = required - len(suitable)
        if len(unassessed) == remaining_needed:
            primaries = tuple(candidate for candidate in viable if candidate in suitable or candidate in unassessed)
            return ProviderAssignment(
                requirement_id=candidate_set.requirement_id,
                encounter_id=candidate_set.encounter_id,
                requirement_type=candidate_set.requirement_type,
                status=ProviderAssignmentStatus.ASSIGNED,
                primary_providers=primaries,
                backup_providers=(),
                unresolved_candidates=unresolved,
                conflicting_candidates=(),
                explanation=(
                    "Explicit suitability exclusions leave exactly the required viable "
                    "providers; no arbitrary tie-break is needed."
                ),
                unsuitable_candidates=unsuitable,
                suitability_unresolved_candidates=suitability_unresolved,
            )

        return ProviderAssignment(
            requirement_id=candidate_set.requirement_id,
            encounter_id=candidate_set.encounter_id,
            requirement_type=candidate_set.requirement_type,
            status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
            primary_providers=(),
            backup_providers=available,
            unresolved_candidates=unresolved,
            conflicting_candidates=(),
            explanation=(
                "Suitability evidence narrows the candidates but does not uniquely fill "
                "the required provider slots. Roster order is not a strategy rule."
            ),
            unsuitable_candidates=unsuitable,
            suitability_unresolved_candidates=suitability_unresolved,
        )

    @staticmethod
    def _validate_suitability_set(
        candidate_set: ProviderCandidateSet,
        suitability_set: ProviderSuitabilitySet,
    ) -> None:
        if suitability_set.encounter_id != candidate_set.encounter_id:
            raise ValueError("suitability set encounter_id does not match candidate set")
        if suitability_set.requirement_type != candidate_set.requirement_type:
            raise ValueError("suitability set requirement_type does not match candidate set")

        viable_by_member = {candidate.member_id: candidate for candidate in candidate_set.viable}
        suitability_by_member = {
            row.candidate.member_id: row.candidate for row in suitability_set.candidates
        }
        if set(suitability_by_member) != set(viable_by_member):
            raise ValueError("suitability set must contain every Phase 10 viable provider exactly once")
        for member_id, candidate in suitability_by_member.items():
            if candidate != viable_by_member[member_id]:
                raise ValueError("suitability candidate does not match canonical provider candidate")

    @staticmethod
    def _assign_without_suitability(
        candidate_set: ProviderCandidateSet,
    ) -> ProviderAssignment:
        viable = candidate_set.viable
        unresolved = candidate_set.unresolved
        required = candidate_set.required_provider_count

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
