from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from minmax.build_calculation_context import BuildCalculationContext
from minmax.recovery_timing import DisplayedRecoveryResolver
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_effective_duration import RotationEffectiveDurationOverride
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidence,
)
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_sustain_service import RotationSustainService
from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload


@dataclass(frozen=True)
class RotationCandidateRoleOutputEvidence:
    """Authoritative whole-plan primary-role output for one exact candidate.

    The value is deliberately metric-agnostic here. The owning evaluator decides
    whether it represents effective damage, healing, mitigation, or another explicit
    role-output metric. This composition service only carries a resolved finite value
    forward; unresolved evidence remains unknown and therefore fails closed later.
    """

    candidate_id: str
    value: float | None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("rotation role-output evidence candidate_id is required")
        object.__setattr__(self, "candidate_id", candidate_id)

        if self.value is not None:
            value = float(self.value)
            if not isfinite(value):
                raise ValueError("rotation role-output evidence value must be finite")
            object.__setattr__(self, "value", value)

        object.__setattr__(
            self,
            "unresolved",
            tuple(str(item).strip() for item in self.unresolved if str(item).strip()),
        )

    @property
    def resolved_value(self) -> float | None:
        if self.value is None or self.unresolved:
            return None
        return self.value


class RotationCandidateRoleOutputEvidenceProvider(Protocol):
    """Provide authoritative primary-role output for one exact generated plan."""

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleOutputEvidence: ...


class RotationCandidateProviderWorkloadEvidenceProvider(Protocol):
    """Provide already-evaluated canonical provider workload for one exact candidate."""

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> TeamProviderRotationWorkload: ...


class RotationCandidateCanonicalPlanEvidenceService:
    """Evaluate generated candidates through existing canonical plan mechanics.

    This service is composition only. It does not calculate ESO mechanics itself:
    Phase 4 sustain remains owned by ``RotationSustainService`` and duration/recast
    evidence remains owned by ``RotationDurationAnalysisService``. When supplied,
    provider workload remains owned by the existing team-provider workload path and
    primary-role output remains owned by its explicit whole-plan evaluator.

    Role output stays unknown until an authoritative provider supplies resolved
    evidence for this exact candidate. Assigned-support value remains unresolved
    until its own authoritative provider exists. Primary-role displacement is
    accepted only from a viable, fully resolved canonical provider-workload result;
    missing or blocked evidence never becomes an invented zero.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        sustain_service: RotationSustainService | None = None,
        duration_service: RotationDurationAnalysisService | None = None,
        role_output_evidence_provider: RotationCandidateRoleOutputEvidenceProvider | None = None,
        provider_workload_evidence_provider: (
            RotationCandidateProviderWorkloadEvidenceProvider | None
        ) = None,
        resource: ResourceType = ResourceType.MAGICKA,
        restoration_events: tuple[ResourceRestorationEvent, ...] = (),
        maximum_events: tuple[ResourceMaximumEvent, ...] = (),
        calculation_context: BuildCalculationContext | None = None,
        displayed_recovery_at: DisplayedRecoveryResolver | None = None,
        effective_duration_overrides: tuple[RotationEffectiveDurationOverride, ...] = (),
    ) -> None:
        self.build = build
        self.sustain_service = sustain_service or RotationSustainService()
        self.duration_service = duration_service or RotationDurationAnalysisService()
        self.role_output_evidence_provider = role_output_evidence_provider
        self.provider_workload_evidence_provider = provider_workload_evidence_provider
        self.resource = resource
        self.restoration_events = tuple(restoration_events)
        self.maximum_events = tuple(maximum_events)
        self.calculation_context = calculation_context
        self.displayed_recovery_at = displayed_recovery_at
        self.effective_duration_overrides = tuple(effective_duration_overrides)

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidatePlanEvidence:
        """Evaluate the exact final candidate plan without rebuilding or rescheduling it."""

        sustain = self.sustain_service.evaluate(
            build=self.build,
            plan=candidate.plan,
            resource=self.resource,
            restoration_events=self.restoration_events,
            maximum_events=self.maximum_events,
            calculation_context=self.calculation_context,
            displayed_recovery_at=self.displayed_recovery_at,
        )
        duration = self.duration_service.analyze(
            candidate.plan,
            effective_duration_overrides=self.effective_duration_overrides,
        )

        # Minimum resource is the meaningful deterministic headroom: ending high
        # does not erase a dangerous or failing dip earlier in the rotation.
        sustain_margin = float(sustain.run.sustain.minimum_amount)

        role_output_value: float | None = None
        if self.role_output_evidence_provider is not None:
            role_output = self.role_output_evidence_provider.evaluate_plan(candidate)
            if role_output.candidate_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "rotation role-output evidence candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {role_output.candidate_id!r}"
                )
            role_output_value = role_output.resolved_value

        primary_role_displacement_seconds: float | None = None
        if self.provider_workload_evidence_provider is not None:
            workload = self.provider_workload_evidence_provider.evaluate_plan(candidate)
            if workload.alternative_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "rotation provider-workload evidence candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {workload.alternative_id!r}"
                )
            if workload.viable:
                primary_role_displacement_seconds = float(
                    workload.primary_role_displacement_seconds
                )

        return RotationCandidatePlanEvidence(
            sustain=sustain,
            duration=duration,
            role_output_value=role_output_value,
            sustain_margin=sustain_margin,
            primary_role_displacement_seconds=primary_role_displacement_seconds,
        )


__all__ = [
    "RotationCandidateCanonicalPlanEvidenceService",
    "RotationCandidateProviderWorkloadEvidenceProvider",
    "RotationCandidateRoleOutputEvidence",
    "RotationCandidateRoleOutputEvidenceProvider",
]
