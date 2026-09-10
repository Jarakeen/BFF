from __future__ import annotations

from dataclasses import dataclass, replace
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
    """Authoritative whole-plan primary-role output for one exact candidate."""

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


@dataclass(frozen=True)
class RotationCandidateRestorationEvidence:
    """Candidate-specific runtime restoration events with fail-closed diagnostics."""

    candidate_id: str
    restoration_events: tuple[ResourceRestorationEvent, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id or "").strip()
        if not candidate_id:
            raise ValueError("rotation restoration evidence candidate_id is required")
        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "restoration_events", tuple(self.restoration_events))
        object.__setattr__(
            self,
            "unresolved",
            tuple(str(item).strip() for item in self.unresolved if str(item).strip()),
        )


class RotationCandidateRoleOutputEvidenceProvider(Protocol):
    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleOutputEvidence: ...


class RotationCandidateRestorationEvidenceProvider(Protocol):
    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRestorationEvidence: ...


class RotationCandidateProviderWorkloadEvidenceProvider(Protocol):
    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> TeamProviderRotationWorkload: ...


class RotationCandidateCanonicalPlanEvidenceService:
    """Evaluate generated candidates through existing canonical plan mechanics.

    This service is composition only. Phase 4 sustain remains owned by
    ``RotationSustainService`` and duration/recast evidence remains owned by
    ``RotationDurationAnalysisService``. Candidate-specific restoration providers may
    add already-resolved runtime restoration events before sustain evaluation; this
    service never calculates the restoration amount itself.

    Role output stays unknown until an authoritative provider supplies resolved
    evidence for this exact candidate. Provider workload may supply two separate
    support-role measurements: primary-role displacement and, only when the canonical
    recipient and temporal coverage result objects are both present and satisfied,
    assigned-support temporal coverage ratio. The adapter never derives support from
    hand-copied booleans and never combines unlike coverage/burden dimensions into a
    weighted score.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        sustain_service: RotationSustainService | None = None,
        duration_service: RotationDurationAnalysisService | None = None,
        role_output_evidence_provider: RotationCandidateRoleOutputEvidenceProvider | None = None,
        restoration_evidence_provider: RotationCandidateRestorationEvidenceProvider | None = None,
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
        self.restoration_evidence_provider = restoration_evidence_provider
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

        candidate_restoration_events: tuple[ResourceRestorationEvent, ...] = ()
        restoration_unresolved: tuple[str, ...] = ()
        if self.restoration_evidence_provider is not None:
            restoration = self.restoration_evidence_provider.evaluate_plan(candidate)
            if restoration.candidate_id.casefold() != candidate.candidate_id.casefold():
                raise ValueError(
                    "rotation restoration evidence candidate mismatch: "
                    f"expected {candidate.candidate_id!r}, got {restoration.candidate_id!r}"
                )
            candidate_restoration_events = tuple(restoration.restoration_events)
            restoration_unresolved = tuple(restoration.unresolved)

        sustain = self.sustain_service.evaluate(
            build=self.build,
            plan=candidate.plan,
            resource=self.resource,
            restoration_events=self.restoration_events + candidate_restoration_events,
            maximum_events=self.maximum_events,
            calculation_context=self.calculation_context,
            displayed_recovery_at=self.displayed_recovery_at,
        )
        if restoration_unresolved:
            sustain = replace(
                sustain,
                unresolved=self._dedupe(tuple(sustain.unresolved) + restoration_unresolved),
            )

        duration = self.duration_service.analyze(
            candidate.plan,
            effective_duration_overrides=self.effective_duration_overrides,
        )

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

        assigned_support_value: float | None = None
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
                recipient = workload.recipient_coverage_result
                temporal = workload.temporal_coverage_result
                if (
                    recipient is not None
                    and temporal is not None
                    and recipient.fully_covered
                    and temporal.full_requirement_met
                ):
                    coverage_ratio = float(temporal.coverage_ratio)
                    if not isfinite(coverage_ratio) or not 0.0 <= coverage_ratio <= 1.0:
                        raise ValueError(
                            "canonical provider temporal coverage ratio must be finite between 0 and 1"
                        )
                    assigned_support_value = coverage_ratio

        return RotationCandidatePlanEvidence(
            sustain=sustain,
            duration=duration,
            role_output_value=role_output_value,
            assigned_support_value=assigned_support_value,
            sustain_margin=sustain_margin,
            primary_role_displacement_seconds=primary_role_displacement_seconds,
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationCandidateCanonicalPlanEvidenceService",
    "RotationCandidateProviderWorkloadEvidenceProvider",
    "RotationCandidateRestorationEvidence",
    "RotationCandidateRestorationEvidenceProvider",
    "RotationCandidateRoleOutputEvidence",
    "RotationCandidateRoleOutputEvidenceProvider",
]
