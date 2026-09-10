from __future__ import annotations

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


class RotationCandidateCanonicalPlanEvidenceService:
    """Evaluate generated candidates through existing canonical plan mechanics.

    This service is composition only. It does not calculate ESO mechanics itself:
    Phase 4 sustain remains owned by ``RotationSustainService`` and duration/recast
    evidence remains owned by ``RotationDurationAnalysisService``. Role output,
    assigned support value, and primary-role displacement stay unresolved until
    their authoritative role/workload providers supply them.
    """

    def __init__(
        self,
        *,
        build: PlayerBuild,
        sustain_service: RotationSustainService | None = None,
        duration_service: RotationDurationAnalysisService | None = None,
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

        return RotationCandidatePlanEvidence(
            sustain=sustain,
            duration=duration,
            sustain_margin=sustain_margin,
        )


__all__ = ["RotationCandidateCanonicalPlanEvidenceService"]
