from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.build_model import PlayerBuild
from services.encounter_build_capability_adapter import SavedBuildEncounterCapabilityAdapter
from services.encounter_provider_assignment import (
    EncounterProviderAssignmentService,
    ProviderAssignment,
)
from services.encounter_provider_candidate import EncounterProviderCandidateService
from services.encounter_repository import EncounterRepository
from services.encounter_requirement_overlay import EncounterRequirementOverlayService
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.raid_coverage_encounter_adapter import RaidCoverageEncounterAdapter
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.saved_build_capability_service import (
    SavedBuildCapabilityAudit,
    SavedBuildCapabilityService,
)


@dataclass(frozen=True)
class BuildCandidateProviderScope:
    """Re-evaluate Phase 10/11 provider assignments for one changing roster member.

    The baseline roster is audited once and bound to canonical member identity. A
    candidate may replace exactly one member's build; every other roster member and
    the encounter/provider configuration remain fixed. Provider truth is recomputed
    through the existing Phase 10 evidence and Phase 11 assignment services rather
    than copied or inferred inside Phase 12.
    """

    encounter_id: str
    member_id: str
    baseline_audits: tuple[SavedBuildCapabilityAudit, ...]
    baseline_assignments: tuple[ProviderAssignment, ...]
    capability_service: SavedBuildCapabilityService
    roster_evaluator: EncounterRosterEvaluator
    candidate_service: EncounterProviderCandidateService
    assignment_service: EncounterProviderAssignmentService

    @classmethod
    def create(
        cls,
        *,
        encounter_id: str,
        member_id: str,
        roster_builds: tuple[PlayerBuild, ...],
        capability_service: SavedBuildCapabilityService,
        roster_evaluator: EncounterRosterEvaluator,
        candidate_service: EncounterProviderCandidateService | None = None,
        assignment_service: EncounterProviderAssignmentService | None = None,
    ) -> "BuildCandidateProviderScope":
        normalized_encounter = str(encounter_id or "").strip()
        normalized_member = str(member_id or "").strip()
        if not normalized_encounter:
            raise ValueError("provider scope encounter_id is required")
        if not normalized_member:
            raise ValueError("provider scope member_id is required")
        if not roster_builds:
            raise ValueError("provider scope requires at least one saved roster build")

        audits = tuple(capability_service.audit_build(build) for build in roster_builds)
        member_ids = tuple(
            SavedBuildEncounterCapabilityAdapter.member_id(audit) for audit in audits
        )
        if len(member_ids) != len(set(member_ids)):
            raise ValueError(
                "provider scope roster must contain exactly one authoritative build per member"
            )
        if normalized_member not in member_ids:
            raise ValueError(
                f"provider scope member {normalized_member!r} is not present in the saved roster"
            )

        provider_candidates = candidate_service or EncounterProviderCandidateService()
        provider_assignments = assignment_service or EncounterProviderAssignmentService()
        baseline_assignments = _resolve_assignments(
            encounter_id=normalized_encounter,
            audits=audits,
            roster_evaluator=roster_evaluator,
            candidate_service=provider_candidates,
            assignment_service=provider_assignments,
        )
        return cls(
            encounter_id=normalized_encounter,
            member_id=normalized_member,
            baseline_audits=audits,
            baseline_assignments=baseline_assignments,
            capability_service=capability_service,
            roster_evaluator=roster_evaluator,
            candidate_service=provider_candidates,
            assignment_service=provider_assignments,
        )

    def assignments_for(self, candidate_build: PlayerBuild) -> tuple[ProviderAssignment, ...]:
        """Return assignments after replacing exactly this scope's member build."""

        candidate_audit = self.capability_service.audit_build(candidate_build)
        candidate_member_id = SavedBuildEncounterCapabilityAdapter.member_id(candidate_audit)
        if candidate_member_id != self.member_id:
            raise ValueError(
                "candidate provider identity changed while replacing a saved roster member: "
                f"expected {self.member_id!r}, got {candidate_member_id!r}"
            )

        audits = tuple(
            candidate_audit
            if SavedBuildEncounterCapabilityAdapter.member_id(audit) == self.member_id
            else audit
            for audit in self.baseline_audits
        )
        return _resolve_assignments(
            encounter_id=self.encounter_id,
            audits=audits,
            roster_evaluator=self.roster_evaluator,
            candidate_service=self.candidate_service,
            assignment_service=self.assignment_service,
        )


def build_default_raid_provider_scope(
    *,
    encounter_id: str,
    member_id: str,
    roster_builds: tuple[PlayerBuild, ...],
    capability_service: SavedBuildCapabilityService,
    data_root: Path,
    database_path: Path,
) -> BuildCandidateProviderScope:
    """Bind Phase 12 to the same explicit default raid-coverage overlay as Phase 11."""

    coverage_adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)
    repository = EncounterRepository(
        data_root / "eso_info" / "bosses",
        data_root / "encounter_evidence",
        database_path=database_path,
    )
    base_service = EncounterService(repository)
    encounter_service = EncounterRequirementOverlayService(
        base_service,
        {encounter_id: coverage_adapter.requirements(encounter_id)},
    )
    roster_evaluator = EncounterRosterEvaluator(
        encounter_service,
        SavedBuildEncounterCapabilityAdapter(coverage_adapter.capability_identity_maps()),
        requirement_semantics=coverage_adapter.requirement_semantics(),
        required_provider_counts=coverage_adapter.required_provider_counts(encounter_id),
    )
    return BuildCandidateProviderScope.create(
        encounter_id=encounter_id,
        member_id=member_id,
        roster_builds=roster_builds,
        capability_service=capability_service,
        roster_evaluator=roster_evaluator,
    )


def _resolve_assignments(
    *,
    encounter_id: str,
    audits: tuple[SavedBuildCapabilityAudit, ...],
    roster_evaluator: EncounterRosterEvaluator,
    candidate_service: EncounterProviderCandidateService,
    assignment_service: EncounterProviderAssignmentService,
) -> tuple[ProviderAssignment, ...]:
    report = roster_evaluator.evaluate_saved_build_audits(encounter_id, audits)
    candidate_sets = candidate_service.candidates(report, audits)
    return assignment_service.assign(candidate_sets)
