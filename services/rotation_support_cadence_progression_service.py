from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_effect_uptime_service import RotationEffectUptimeAssessment
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluatedCandidate,
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhood,
    RotationSupportCadenceNeighborhoodObligation,
)
from services.rotation_support_cadence_recommendation_service import (
    RotationSupportCadenceRecommendationResult,
)
from services.rotation_sustain_service import RotationSustainProjection


class _NeighborhoodGenerator(Protocol):
    def generate(
        self,
        *,
        seed_plan: RotationPlan,
        obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...],
        priorities: AbilityPriorityList | None = None,
    ) -> RotationSupportCadenceNeighborhood: ...


class _CandidateEvaluator(Protocol):
    def evaluate(
        self,
        *,
        build: PlayerBuild,
        baseline_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidates: tuple[object, ...],
        context: RotationSupportCadenceEvaluationContext | None = None,
    ) -> tuple[RotationSupportCadenceEvaluatedCandidate, ...]: ...

    def rank(
        self,
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
        *,
        effect_uptime_assessments_by_candidate: Mapping[
            str, tuple[RotationEffectUptimeAssessment, ...]
        ] | None = None,
    ) -> tuple[RotationEffectObligationRankingResult, ...]: ...


class _RecommendationSelector(Protocol):
    def recommend(
        self,
        *,
        evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...],
        ranking: tuple[RotationEffectObligationRankingResult, ...],
    ) -> RotationSupportCadenceRecommendationResult: ...


@dataclass(frozen=True)
class RotationSupportCadenceProgressionStep:
    """One bounded optimization step with enough evidence to continue safely."""

    seed_plan: RotationPlan
    seed_sustain: RotationSustainProjection
    neighborhood: RotationSupportCadenceNeighborhood
    evaluated: tuple[RotationSupportCadenceEvaluatedCandidate, ...]
    ranking: tuple[RotationEffectObligationRankingResult, ...]
    recommendation: RotationSupportCadenceRecommendationResult
    next_seed_plan: RotationPlan
    next_seed_sustain: RotationSustainProjection
    promoted_candidate_id: str | None

    @property
    def advanced(self) -> bool:
        return self.promoted_candidate_id is not None

    @property
    def unresolved(self) -> tuple[str, ...]:
        return self.neighborhood.unresolved


class RotationSupportCadenceProgressionService:
    """Compose one progressive local-search step over support cadence candidates.

    The current seed is deliberately used as the scorecard baseline for this step.
    A neighborhood is generated around that complete rotation, every neighbor flows
    through the existing evaluation/ranking pipeline, and only the final eligible
    recommendation may become the next seed. If no candidate is recommendable, the
    current seed and its already-known sustain projection are retained unchanged.

    This service performs exactly one step. It does not loop, set convergence policy,
    form Cartesian products, or bypass unresolved mechanics. Callers may explicitly
    feed ``next_seed_plan`` and ``next_seed_sustain`` into another step when further
    progressive optimization is desired.
    """

    def __init__(
        self,
        *,
        neighborhood_service: _NeighborhoodGenerator,
        evaluation_service: _CandidateEvaluator,
        recommendation_service: _RecommendationSelector,
    ) -> None:
        self.neighborhood_service = neighborhood_service
        self.evaluation_service = evaluation_service
        self.recommendation_service = recommendation_service

    def step(
        self,
        *,
        build: PlayerBuild,
        seed_plan: RotationPlan,
        seed_sustain: RotationSustainProjection,
        obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...],
        priorities: AbilityPriorityList | None = None,
        evaluation_context: RotationSupportCadenceEvaluationContext | None = None,
        effect_uptime_assessments_by_candidate: Mapping[
            str, tuple[RotationEffectUptimeAssessment, ...]
        ] | None = None,
    ) -> RotationSupportCadenceProgressionStep:
        neighborhood = self.neighborhood_service.generate(
            seed_plan=seed_plan,
            obligations=obligations,
            priorities=priorities,
        )
        evaluated = self.evaluation_service.evaluate(
            build=build,
            baseline_plan=seed_plan,
            baseline_sustain=seed_sustain,
            candidates=neighborhood.candidates,
            context=evaluation_context,
        )
        ranking = self.evaluation_service.rank(
            evaluated,
            effect_uptime_assessments_by_candidate=effect_uptime_assessments_by_candidate,
        )
        recommendation = self.recommendation_service.recommend(
            evaluated=evaluated,
            ranking=ranking,
        )

        recommended = recommendation.recommended
        if recommended is None:
            next_seed_plan = seed_plan
            next_seed_sustain = seed_sustain
            promoted_candidate_id = None
        else:
            promoted = recommended.evaluated
            next_seed_plan = promoted.candidate.plan
            next_seed_sustain = promoted.sustain
            promoted_candidate_id = promoted.candidate_id

        return RotationSupportCadenceProgressionStep(
            seed_plan=seed_plan,
            seed_sustain=seed_sustain,
            neighborhood=neighborhood,
            evaluated=evaluated,
            ranking=ranking,
            recommendation=recommendation,
            next_seed_plan=next_seed_plan,
            next_seed_sustain=next_seed_sustain,
            promoted_candidate_id=promoted_candidate_id,
        )


__all__ = [
    "RotationSupportCadenceProgressionService",
    "RotationSupportCadenceProgressionStep",
]
