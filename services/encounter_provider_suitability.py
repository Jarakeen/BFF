from __future__ import annotations

"""Explicit Phase 11 suitability evidence for already-viable providers.

Suitability is not capability. Phase 10 remains authoritative for whether a roster
member can provide an encounter requirement at all. This layer records additional,
source-backed facts that may later distinguish several viable providers without
inventing a ranking from roster order, build names, or generic tooltip prose.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateSet,
    ProviderCandidateStatus,
)


class ProviderSuitabilityDimension(str, Enum):
    ROLE = "role"
    BUILD = "build"
    ACTIVE_BAR = "active_bar"
    ELIGIBILITY = "eligibility"
    UPTIME = "uptime"
    RANGE = "range"
    TARGET_TYPE = "target_type"
    CONDITION = "condition"
    POSITIONING = "positioning"
    CONFLICT = "conflict"
    PLAYER_RESTRICTION = "player_restriction"


class ProviderSuitabilityAssessment(str, Enum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"


class ProviderSuitabilityStatus(str, Enum):
    SUITABLE = "suitable"
    UNSUITABLE = "unsuitable"
    UNRESOLVED = "unresolved"
    UNASSESSED = "unassessed"


@dataclass(frozen=True)
class ProviderSuitabilityEvidence:
    """One explicit suitability fact for one candidate and exact requirement."""

    requirement_id: str
    member_id: str
    dimension: ProviderSuitabilityDimension
    assessment: ProviderSuitabilityAssessment
    source: str
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise ValueError("requirement_id must be non-empty")
        if not self.member_id:
            raise ValueError("member_id must be non-empty")
        if not self.source:
            raise ValueError("source must be non-empty")
        if not isinstance(self.dimension, ProviderSuitabilityDimension):
            raise ValueError("dimension must be ProviderSuitabilityDimension")
        if not isinstance(self.assessment, ProviderSuitabilityAssessment):
            raise ValueError("assessment must be ProviderSuitabilityAssessment")


@dataclass(frozen=True)
class ProviderSuitability:
    """Aggregated explicit suitability state for one already-viable provider."""

    candidate: ProviderCandidate
    status: ProviderSuitabilityStatus
    evidence: tuple[ProviderSuitabilityEvidence, ...]

    @property
    def failed_dimensions(self) -> tuple[ProviderSuitabilityDimension, ...]:
        return tuple(
            dict.fromkeys(
                row.dimension
                for row in self.evidence
                if row.assessment == ProviderSuitabilityAssessment.UNSATISFIED
            )
        )

    @property
    def unresolved_dimensions(self) -> tuple[ProviderSuitabilityDimension, ...]:
        return tuple(
            dict.fromkeys(
                row.dimension
                for row in self.evidence
                if row.assessment == ProviderSuitabilityAssessment.UNKNOWN
            )
        )


@dataclass(frozen=True)
class ProviderSuitabilitySet:
    """Suitability projection for every viable candidate of one requirement."""

    requirement_id: str
    encounter_id: str
    requirement_type: str
    candidates: tuple[ProviderSuitability, ...]

    @property
    def suitable(self) -> tuple[ProviderSuitability, ...]:
        return tuple(row for row in self.candidates if row.status == ProviderSuitabilityStatus.SUITABLE)

    @property
    def unsuitable(self) -> tuple[ProviderSuitability, ...]:
        return tuple(row for row in self.candidates if row.status == ProviderSuitabilityStatus.UNSUITABLE)

    @property
    def unresolved(self) -> tuple[ProviderSuitability, ...]:
        return tuple(row for row in self.candidates if row.status == ProviderSuitabilityStatus.UNRESOLVED)

    @property
    def unassessed(self) -> tuple[ProviderSuitability, ...]:
        return tuple(row for row in self.candidates if row.status == ProviderSuitabilityStatus.UNASSESSED)


class EncounterProviderSuitabilityService:
    """Aggregate explicit suitability evidence without choosing providers.

    Only Phase 10 VIABLE candidates may receive suitability analysis. UNRESOLVED and
    CONFLICTING provider candidates stay in their Phase 10 states and are not made
    viable by favorable Phase 11 facts.

    Status precedence is conservative:

    * any UNSATISFIED fact -> UNSUITABLE
    * otherwise any UNKNOWN fact -> UNRESOLVED
    * otherwise one or more SATISFIED facts -> SUITABLE
    * no suitability facts -> UNASSESSED

    Conflicting assessments for the same dimension are rejected rather than silently
    collapsed into whichever row happened to appear last.
    """

    def assess(
        self,
        candidate_sets: tuple[ProviderCandidateSet, ...],
        evidence: tuple[ProviderSuitabilityEvidence, ...] = (),
    ) -> tuple[ProviderSuitabilitySet, ...]:
        candidate_lookup: dict[tuple[str, str], ProviderCandidate] = {}
        viable_keys: set[tuple[str, str]] = set()
        requirement_ids: set[str] = set()

        for candidate_set in candidate_sets:
            if candidate_set.requirement_id in requirement_ids:
                raise ValueError("candidate_sets cannot duplicate requirement_id")
            requirement_ids.add(candidate_set.requirement_id)
            for candidate in candidate_set.candidates:
                key = (candidate_set.requirement_id, candidate.member_id)
                candidate_lookup[key] = candidate
                if candidate.status == ProviderCandidateStatus.VIABLE:
                    viable_keys.add(key)

        evidence_by_candidate: dict[
            tuple[str, str], list[ProviderSuitabilityEvidence]
        ] = {}
        assessments_by_dimension: dict[
            tuple[str, str, ProviderSuitabilityDimension], ProviderSuitabilityAssessment
        ] = {}

        for row in evidence:
            key = (row.requirement_id, row.member_id)
            candidate = candidate_lookup.get(key)
            if candidate is None:
                raise ValueError(
                    "suitability evidence references a member/requirement that is not a provider candidate"
                )
            if key not in viable_keys:
                raise ValueError(
                    "suitability evidence may only assess Phase 10 viable provider candidates"
                )

            dimension_key = (row.requirement_id, row.member_id, row.dimension)
            existing = assessments_by_dimension.get(dimension_key)
            if existing is not None and existing != row.assessment:
                raise ValueError(
                    "conflicting suitability assessments exist for the same requirement/member/dimension"
                )
            assessments_by_dimension[dimension_key] = row.assessment
            evidence_by_candidate.setdefault(key, []).append(row)

        results: list[ProviderSuitabilitySet] = []
        for candidate_set in candidate_sets:
            rows: list[ProviderSuitability] = []
            for candidate in candidate_set.viable:
                candidate_evidence = tuple(
                    evidence_by_candidate.get(
                        (candidate_set.requirement_id, candidate.member_id),
                        (),
                    )
                )
                assessments = {row.assessment for row in candidate_evidence}

                if ProviderSuitabilityAssessment.UNSATISFIED in assessments:
                    status = ProviderSuitabilityStatus.UNSUITABLE
                elif ProviderSuitabilityAssessment.UNKNOWN in assessments:
                    status = ProviderSuitabilityStatus.UNRESOLVED
                elif ProviderSuitabilityAssessment.SATISFIED in assessments:
                    status = ProviderSuitabilityStatus.SUITABLE
                else:
                    status = ProviderSuitabilityStatus.UNASSESSED

                rows.append(
                    ProviderSuitability(
                        candidate=candidate,
                        status=status,
                        evidence=candidate_evidence,
                    )
                )

            results.append(
                ProviderSuitabilitySet(
                    requirement_id=candidate_set.requirement_id,
                    encounter_id=candidate_set.encounter_id,
                    requirement_type=candidate_set.requirement_type,
                    candidates=tuple(rows),
                )
            )

        return tuple(results)
