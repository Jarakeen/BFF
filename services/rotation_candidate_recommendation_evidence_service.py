from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from minmax.encounter_requirements import EncounterRequirementSet
from minmax.rotation_action_cooldown import RotationActionCooldownRequirement
from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_action_range import (
    RotationActionRangeRequirement,
    RotationTargetDistanceWindow,
)
from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetStateWindow,
)
from minmax.rotation_bar_availability import RotationBarAvailabilityWindow
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from minmax.rotation_ultimate_affordability import RotationUltimateAffordabilityRequirement
from minmax.support_coverage import SupportCoverage
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationEvidence,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_runtime_uptime_service import (
    RotationRuntimeUptimeObjective,
    RotationRuntimeUptimeRequirement,
)
from services.rotation_sustain_service import RotationSustainProjection


@dataclass(frozen=True)
class RotationCandidatePlanEvidence:
    """Canonical evaluated evidence for one generated whole rotation plan.

    The adapter does not calculate these measurements. Damage/healing/support,
    sustain, duration, and workload services remain authoritative and provide the
    values here. Unknown role-policy evidence stays ``None`` so recommendation
    ranking can fail closed rather than inventing a zero.
    """

    sustain: RotationSustainProjection
    duration: RotationDurationProjection | None = None
    role_output_value: float | None = None
    assigned_support_value: float | None = None
    sustain_margin: float | None = None
    primary_role_displacement_seconds: float | None = None


class RotationCandidatePlanEvidenceProvider(Protocol):
    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidatePlanEvidence: ...


@dataclass(frozen=True)
class RotationCandidateSharedEvaluationContext:
    """Caller-proven hard obligations shared by every candidate in one family."""

    demands: tuple[RotationDemandWindow, ...] = ()
    demand_requirements: tuple[RotationDemandActionRequirement, ...] = ()
    reserve_requirements: tuple[RotationResourceReserveRequirement, ...] = ()
    bar_availability_windows: tuple[RotationBarAvailabilityWindow, ...] = ()
    cooldown_requirements: tuple[RotationActionCooldownRequirement, ...] = ()
    occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...] = ()
    range_requirements: tuple[RotationActionRangeRequirement, ...] = ()
    target_distance_windows: tuple[RotationTargetDistanceWindow, ...] = ()
    target_requirements: tuple[RotationActionTargetRequirement, ...] = ()
    target_state_windows: tuple[RotationTargetStateWindow, ...] = ()
    slot_requirements: tuple[RotationActionSlotRequirement, ...] = ()
    ultimate_affordability_requirement: RotationUltimateAffordabilityRequirement | None = None
    encounter_requirements: EncounterRequirementSet | None = None
    support_coverage: SupportCoverage | None = None
    runtime_uptime_requirements: tuple[RotationRuntimeUptimeRequirement, ...] = ()
    runtime_uptime_objective: RotationRuntimeUptimeObjective | None = None


class RotationCandidateRecommendationEvidenceService:
    """Bridge generated plans into the existing scorecard/recommendation contracts.

    This is intentionally an adapter, not a second mechanics engine. It asks the
    caller's canonical plan-evidence provider for sustain/duration/role measurements,
    feeds the plans and shared obligations through ``RotationCandidateScorecardService``,
    then returns the exact evidence object consumed by the recommendation composer.

    Baseline evidence is cached by candidate identity because the recommendation
    composer evaluates every sibling against the same baseline. No candidate may
    silently substitute a different baseline plan.
    """

    def __init__(
        self,
        *,
        plan_evidence_provider: RotationCandidatePlanEvidenceProvider,
        context: RotationCandidateSharedEvaluationContext | None = None,
        scorecard_service: RotationCandidateScorecardService | None = None,
    ) -> None:
        self.plan_evidence_provider = plan_evidence_provider
        self.context = context or RotationCandidateSharedEvaluationContext()
        self.scorecard_service = scorecard_service or RotationCandidateScorecardService()
        self._baseline_key: str | None = None
        self._baseline_evidence: RotationCandidatePlanEvidence | None = None

    def evaluate(
        self,
        *,
        baseline: GeneratedRotationCandidate,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRecommendationEvidence:
        baseline_key = baseline.candidate_id.casefold()
        if self._baseline_key is not None and self._baseline_key != baseline_key:
            raise ValueError(
                "rotation recommendation evidence service cannot mix candidate families: "
                f"baseline changed from {self._baseline_key!r} to {baseline.candidate_id!r}"
            )

        if self._baseline_evidence is None:
            self._baseline_key = baseline_key
            self._baseline_evidence = self.plan_evidence_provider.evaluate_plan(baseline)

        if candidate.candidate_id.casefold() == baseline_key:
            candidate_evidence = self._baseline_evidence
        else:
            candidate_evidence = self.plan_evidence_provider.evaluate_plan(candidate)

        context = self.context
        scorecard = self.scorecard_service.compare(
            baseline_plan=baseline.plan,
            candidate_plan=candidate.plan,
            baseline_sustain=self._baseline_evidence.sustain,
            candidate_sustain=candidate_evidence.sustain,
            demands=context.demands,
            demand_requirements=context.demand_requirements,
            reserve_requirements=context.reserve_requirements,
            bar_availability_windows=context.bar_availability_windows,
            cooldown_requirements=context.cooldown_requirements,
            occupancy_requirements=context.occupancy_requirements,
            range_requirements=context.range_requirements,
            target_distance_windows=context.target_distance_windows,
            target_requirements=context.target_requirements,
            target_state_windows=context.target_state_windows,
            slot_requirements=context.slot_requirements,
            ultimate_affordability_requirement=context.ultimate_affordability_requirement,
            encounter_requirements=context.encounter_requirements,
            support_coverage=context.support_coverage,
            candidate_duration=candidate_evidence.duration,
            runtime_uptime_requirements=context.runtime_uptime_requirements,
            runtime_uptime_objective=context.runtime_uptime_objective,
        )
        return RotationCandidateRecommendationEvidence(
            candidate_id=candidate.candidate_id,
            scorecard=scorecard,
            role_output_value=candidate_evidence.role_output_value,
            assigned_support_value=candidate_evidence.assigned_support_value,
            sustain_margin=candidate_evidence.sustain_margin,
            primary_role_displacement_seconds=(
                candidate_evidence.primary_role_displacement_seconds
            ),
        )


__all__ = [
    "RotationCandidatePlanEvidence",
    "RotationCandidatePlanEvidenceProvider",
    "RotationCandidateRecommendationEvidenceService",
    "RotationCandidateSharedEvaluationContext",
]
