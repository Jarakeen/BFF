from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Mapping, Protocol

from minmax.build_calculation_context import BuildCalculationContext
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.restoration_events import ResourceRestorationEvent
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
from minmax.rotation_plan import RotationPlan
from minmax.rotation_resource_reserve import RotationResourceReserveRequirement
from minmax.rotation_ultimate_affordability import RotationUltimateAffordabilityRequirement
from minmax.support_coverage import SupportCoverage
from minmax.recovery_timing import DisplayedRecoveryResolver
from models.build_model import PlayerBuild
from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
    RotationEffectObligationCandidate,
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_ranking_service import RotationCandidateRankingInput
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecard,
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeAssessment
from services.rotation_runtime_uptime_service import (
    RotationRuntimeUptimeObjective,
    RotationRuntimeUptimeRequirement,
)
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadencePlanCandidate,
)
from services.rotation_sustain_service import RotationSustainProjection, RotationSustainService


CandidateHardObligationResolver = Callable[[RotationPlan], tuple[str, ...]]


class _SustainEvaluator(Protocol):
    def evaluate(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType = ResourceType.MAGICKA,
        restoration_events: tuple[ResourceRestorationEvent, ...] = (),
        maximum_events: tuple[ResourceMaximumEvent, ...] = (),
        calculation_context: BuildCalculationContext | None = None,
        displayed_recovery_at: DisplayedRecoveryResolver | None = None,
    ) -> RotationSustainProjection: ...


class _ScorecardEvaluator(Protocol):
    def compare(self, **kwargs: object) -> RotationCandidateScorecard: ...


class _EffectObligationRanker(Protocol):
    def rank(
        self,
        candidates: tuple[RotationEffectObligationCandidate, ...],
    ) -> tuple[RotationEffectObligationRankingResult, ...]: ...


@dataclass(frozen=True)
class RotationSupportCadenceEvaluationContext:
    """Caller-supplied evidence used to evaluate complete cadence candidates.

    This object contains no inferred encounter policy. Its fields mirror existing
    sustain and scorecard inputs so candidate evaluation remains a composition step,
    not a second mechanics implementation. ``candidate_hard_obligation_resolver``
    is explicitly candidate-specific and runs against each completed plan before
    ranking; any returned evidence item becomes a hard-failing candidate-specific
    unresolved item through the existing scorecard contract.
    """

    resource: ResourceType = ResourceType.MAGICKA
    restoration_events: tuple[ResourceRestorationEvent, ...] = ()
    maximum_events: tuple[ResourceMaximumEvent, ...] = ()
    calculation_context: BuildCalculationContext | None = None
    displayed_recovery_at: DisplayedRecoveryResolver | None = None
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
    candidate_hard_obligation_resolver: CandidateHardObligationResolver | None = None


@dataclass(frozen=True)
class RotationSupportCadenceEvaluatedCandidate:
    """One complete cadence candidate with mechanics evidence ready for ranking."""

    candidate: RotationSupportCadencePlanCandidate
    sustain: RotationSustainProjection
    scorecard: RotationCandidateScorecard
    ranking_input: RotationCandidateRankingInput

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id

    @property
    def rationale(self) -> str:
        return self.candidate.cadence.rationale


class RotationSupportCadenceEvaluationService:
    """Bridge complete cadence plans into existing sustain/scorecard/ranking layers.

    Candidate construction remains owned by RotationSupportCadenceCandidateService.
    This adapter evaluates each already-complete plan with the canonical sustain and
    scorecard services, then emits the existing ranking input. Effect-uptime evidence
    stays explicit and build-aware; callers may provide those assessments to ``rank``
    rather than having this PlayerBuild adapter invent or duplicate CharacterBuild
    effect semantics.
    """

    def __init__(
        self,
        *,
        sustain_service: _SustainEvaluator | None = None,
        scorecard_service: _ScorecardEvaluator | None = None,
        effect_obligation_ranker: _EffectObligationRanker | None = None,
    ) -> None:
        self.sustain_service = sustain_service or RotationSustainService()
        self.scorecard_service = scorecard_service or RotationCandidateScorecardService()
        self.effect_obligation_ranker = (
            effect_obligation_ranker or RotationCandidateEffectObligationService()
        )

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        baseline_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidates: tuple[RotationSupportCadencePlanCandidate, ...],
        context: RotationSupportCadenceEvaluationContext | None = None,
    ) -> tuple[RotationSupportCadenceEvaluatedCandidate, ...]:
        evidence = context or RotationSupportCadenceEvaluationContext()
        self._validate_candidate_ids(candidates)

        evaluated: list[RotationSupportCadenceEvaluatedCandidate] = []
        for candidate in candidates:
            sustain = self.sustain_service.evaluate(
                build=build,
                plan=candidate.plan,
                resource=evidence.resource,
                restoration_events=evidence.restoration_events,
                maximum_events=evidence.maximum_events,
                calculation_context=evidence.calculation_context,
                displayed_recovery_at=evidence.displayed_recovery_at,
            )
            scorecard = self.scorecard_service.compare(
                baseline_plan=baseline_plan,
                candidate_plan=candidate.plan,
                baseline_sustain=baseline_sustain,
                candidate_sustain=sustain,
                demands=evidence.demands,
                demand_requirements=evidence.demand_requirements,
                reserve_requirements=evidence.reserve_requirements,
                bar_availability_windows=evidence.bar_availability_windows,
                cooldown_requirements=evidence.cooldown_requirements,
                occupancy_requirements=evidence.occupancy_requirements,
                range_requirements=evidence.range_requirements,
                target_distance_windows=evidence.target_distance_windows,
                target_requirements=evidence.target_requirements,
                target_state_windows=evidence.target_state_windows,
                slot_requirements=evidence.slot_requirements,
                ultimate_affordability_requirement=evidence.ultimate_affordability_requirement,
                encounter_requirements=evidence.encounter_requirements,
                support_coverage=evidence.support_coverage,
                candidate_duration=candidate.refinement.duration_projection,
                runtime_uptime_requirements=evidence.runtime_uptime_requirements,
                runtime_uptime_objective=evidence.runtime_uptime_objective,
            )
            if evidence.candidate_hard_obligation_resolver is not None:
                added = self._dedupe(
                    evidence.candidate_hard_obligation_resolver(candidate.plan)
                )
                if added:
                    scorecard = replace(
                        scorecard,
                        candidate_specific_unresolved=self._dedupe(
                            scorecard.candidate_specific_unresolved + added
                        ),
                    )
            ranking_input = RotationCandidateRankingInput(
                candidate_id=candidate.candidate_id,
                scorecard=scorecard,
            )
            evaluated.append(
                RotationSupportCadenceEvaluatedCandidate(
                    candidate=candidate,
                    sustain=sustain,
                    scorecard=scorecard,
                    ranking_input=ranking_input,
                )
            )
        return tuple(evaluated)

    def rank(
        self,
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
        *,
        effect_uptime_assessments_by_candidate: Mapping[
            str, tuple[RotationEffectUptimeAssessment, ...]
        ] | None = None,
    ) -> tuple[RotationEffectObligationRankingResult, ...]:
        if not evaluated:
            return ()

        self._validate_evaluated_ids(evaluated)
        assessment_map = self._normalize_assessment_map(
            evaluated,
            effect_uptime_assessments_by_candidate,
        )
        return self.effect_obligation_ranker.rank(
            tuple(
                RotationEffectObligationCandidate(
                    ranking_input=item.ranking_input,
                    effect_uptime_assessments=assessment_map[item.candidate_id.casefold()],
                )
                for item in evaluated
            )
        )

    @staticmethod
    def _validate_candidate_ids(
        candidates: tuple[RotationSupportCadencePlanCandidate, ...],
    ) -> None:
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.candidate_id or "").strip().casefold()
            if not key:
                raise ValueError("support cadence candidate_id must be non-empty")
            if key in seen:
                raise ValueError(
                    f"duplicate support cadence candidate_id: {candidate.candidate_id!r}"
                )
            seen.add(key)

    @staticmethod
    def _validate_evaluated_ids(
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
    ) -> None:
        seen: set[str] = set()
        for item in evaluated:
            key = item.candidate_id.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate evaluated support cadence candidate_id: {item.candidate_id!r}"
                )
            seen.add(key)

    @staticmethod
    def _normalize_assessment_map(
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
        supplied: Mapping[str, tuple[RotationEffectUptimeAssessment, ...]] | None,
    ) -> dict[str, tuple[RotationEffectUptimeAssessment, ...]]:
        expected = {item.candidate_id.casefold() for item in evaluated}
        if supplied is None:
            return {key: () for key in expected}

        normalized: dict[str, tuple[RotationEffectUptimeAssessment, ...]] = {}
        for raw_id, assessments in supplied.items():
            key = str(raw_id or "").strip().casefold()
            if not key:
                raise ValueError("effect uptime assessment candidate_id must be non-empty")
            if key in normalized:
                raise ValueError(
                    f"duplicate effect uptime assessment candidate_id: {raw_id!r}"
                )
            normalized[key] = tuple(assessments)

        if normalized.keys() != expected:
            missing = sorted(expected - normalized.keys())
            unexpected = sorted(normalized.keys() - expected)
            details: list[str] = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise ValueError(
                "effect uptime assessment candidates must exactly match evaluated candidates"
                + (" (" + "; ".join(details) + ")" if details else "")
            )
        return normalized

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
    "CandidateHardObligationResolver",
    "RotationSupportCadenceEvaluatedCandidate",
    "RotationSupportCadenceEvaluationContext",
    "RotationSupportCadenceEvaluationService",
]
