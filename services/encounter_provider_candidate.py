from __future__ import annotations

"""Phase 11 provider-candidate projection over Phase 10 encounter evidence.

This module deliberately does not reinterpret encounter requirements, rescan builds,
or choose a provider. Phase 10 remains authoritative for whether a roster member is
a proven, unresolved, or conflicting provider candidate. Phase 11 binds that exact
evidence to one canonical requirement so later assignment logic has a stable,
auditable input instead of reconstructing coverage from names or tooltip prose.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.coverage_classification import CoverageClassification
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_requirement_evaluation import RequirementSemantics
from services.encounter_roster_evaluation import EncounterRosterEvaluationReport
from services.saved_build_capability_service import SavedBuildCapabilityAudit


class ProviderCandidateStatus(str, Enum):
    VIABLE = "viable"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class ProviderCandidate:
    """One roster member still in consideration for one exact requirement."""

    requirement_id: str
    encounter_id: str
    requirement_type: str
    member_id: str
    character_name: str
    build_name: str
    status: ProviderCandidateStatus
    evidence_sources: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "encounter_id", "requirement_type", "member_id"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must be non-empty")


@dataclass(frozen=True)
class ProviderCandidateSet:
    """All Phase 10-supported candidate states for one exact provider requirement."""

    requirement_id: str
    encounter_id: str
    requirement_type: str
    required_provider_count: int
    coverage_classification: CoverageClassification
    candidates: tuple[ProviderCandidate, ...]

    @property
    def viable(self) -> tuple[ProviderCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.status == ProviderCandidateStatus.VIABLE
        )

    @property
    def unresolved(self) -> tuple[ProviderCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.status == ProviderCandidateStatus.UNRESOLVED
        )

    @property
    def conflicting(self) -> tuple[ProviderCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.status == ProviderCandidateStatus.CONFLICTING
        )


class EncounterProviderCandidateService:
    """Expose Phase 10 provider evidence as exact Phase 11 candidate sets.

    The report's provider/unknown/conflict membership is authoritative. Saved-build
    audits contribute identity and build labels only; they are not re-evaluated here.
    Evidence source strings are carried forward from the Phase 10 adapter so later
    assignment decisions can explain what established each candidacy state.
    """

    def candidates(
        self,
        report: EncounterRosterEvaluationReport,
        audits: tuple[SavedBuildCapabilityAudit, ...],
    ) -> tuple[ProviderCandidateSet, ...]:
        audits_by_member: dict[str, SavedBuildCapabilityAudit] = {}
        member_order: list[str] = []
        for audit in audits:
            member_id = SavedBuildEncounterCapabilityAdapter.member_id(audit)
            if member_id in audits_by_member:
                raise ValueError(
                    "saved-build roster must resolve to unique member identities; "
                    "select one authoritative build per roster member"
                )
            audits_by_member[member_id] = audit
            member_order.append(member_id)

        evidence_sources: dict[tuple[str, str], tuple[str, ...]] = {}
        for evidence in report.capability_evidence:
            key = (evidence.member_id, evidence.capability_type)
            existing = list(evidence_sources.get(key, ()))
            if evidence.source and evidence.source not in existing:
                existing.append(evidence.source)
            evidence_sources[key] = tuple(existing)

        results: list[ProviderCandidateSet] = []
        for requirement in report.requirement_evaluation.results:
            if requirement.semantics != RequirementSemantics.PROVIDER_CAPABILITY:
                continue
            if requirement.required_provider_count is None:
                raise ValueError(
                    f"Provider requirement {requirement.requirement_id!r} has no provider cardinality"
                )

            known_members = (
                set(requirement.providers)
                | set(requirement.unknown_members)
                | set(requirement.conflicting_members)
            )
            missing_audits = known_members - set(audits_by_member)
            if missing_audits:
                raise ValueError(
                    "Phase 10 provider evidence references roster members without saved-build audits: "
                    + ", ".join(sorted(missing_audits))
                )

            candidates: list[ProviderCandidate] = []
            for member_id in member_order:
                if member_id in requirement.conflicting_members:
                    status = ProviderCandidateStatus.CONFLICTING
                elif member_id in requirement.providers:
                    status = ProviderCandidateStatus.VIABLE
                elif member_id in requirement.unknown_members:
                    status = ProviderCandidateStatus.UNRESOLVED
                else:
                    # Explicitly unsupported roster members are not provider candidates.
                    continue

                audit = audits_by_member[member_id]
                candidates.append(
                    ProviderCandidate(
                        requirement_id=requirement.requirement_id,
                        encounter_id=requirement.encounter_id,
                        requirement_type=requirement.requirement_type,
                        member_id=member_id,
                        character_name=audit.character_name,
                        build_name=audit.build_name,
                        status=status,
                        evidence_sources=evidence_sources.get(
                            (member_id, requirement.requirement_type),
                            (),
                        ),
                    )
                )

            results.append(
                ProviderCandidateSet(
                    requirement_id=requirement.requirement_id,
                    encounter_id=requirement.encounter_id,
                    requirement_type=requirement.requirement_type,
                    required_provider_count=requirement.required_provider_count,
                    coverage_classification=requirement.classification,
                    candidates=tuple(candidates),
                )
            )

        return tuple(results)
