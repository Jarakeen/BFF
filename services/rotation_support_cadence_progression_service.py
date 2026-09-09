from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from minmax.character_build.passive_grant import PassiveGrant
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeAssessment,
    RotationEffectUptimeRequirement,
)
from services.rotation_support_cadence_effect_evidence_service import (
    RotationSupportCadenceEffectEvidence,
)
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


class _EffectEvidenceProvider(Protocol):
    def assess(
        self,
        *,
        build: PlayerBuild,
        candidates: tuple[object, ...],
        requirements: tuple[RotationEffectUptimeRequirement, ...],
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationSupportCadenceEffectEvidence: ...


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
    effect_evidence: RotationSupportCadenceEffectEvidence | None = None

    @property
    def advanced(self) -> bool:
        return self.promoted_candidate_id is not None

    @property
    def unresolved(self) -> tuple[str, ...]:
        values = list(self.neighborhood.unresolved)
        if self.effect_evidence is not None:
            values.extend(self.effect_evidence.unresolved)
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


class RotationSupportCadenceProgressionService:
    """Compose one progressive local-search step over support cadence candidates.

    The current seed is deliberately used as the scorecard baseline for this step.
    A neighborhood is generated around that complete rotation, every neighbor flows
    through the existing evaluation/ranking pipeline, and only the final eligible
    recommendation may become the next seed. If no candidate is recommendable, the
    current seed and its already-known sustain projection are retained unchanged.

    When an effect-evidence provider and explicit requirements are supplied, uptime
    evidence is recomputed for this freshly generated neighborhood before ranking.
    This prevents progressive optimization from reusing stale coverage measurements
    after a rotation changes. Callers may still provide an explicit assessment map
    for one-off composition; supplying both evidence paths is rejected.

    This service performs exactly one step. It does not loop, set convergence policy,
    form Cartesian products, or bypass unresolved mechanics.
    """

    def __init__(
        self,
        *,
        neighborhood_service: _NeighborhoodGenerator,
        evaluation_service: _CandidateEvaluator,
        recommendation_service: _RecommendationSelector,
        effect_evidence_service: _EffectEvidenceProvider | None = None,
    ) -> None:
        self.neighborhood_service = neighborhood_service
        self.evaluation_service = evaluation_service
        self.recommendation_service = recommendation_service
        self.effect_evidence_service = effect_evidence_service

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
        effect_uptime_requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationSupportCadenceProgressionStep:
        neighborhood = self.neighborhood_service.generate(
            seed_plan=seed_plan,
            obligations=obligations,
            priorities=priorities,
        )

        effect_evidence: RotationSupportCadenceEffectEvidence | None = None
        effect_map = effect_uptime_assessments_by_candidate
        if effect_map is not None and effect_uptime_requirements:
            raise ValueError(
                "support cadence progression cannot combine explicit effect assessment map "
                "with effect_uptime_requirements"
            )
        if effect_uptime_requirements:
            if self.effect_evidence_service is None:
                raise ValueError(
                    "effect_uptime_requirements need a configured effect_evidence_service"
                )
            effect_evidence = self.effect_evidence_service.assess(
                build=build,
                candidates=neighborhood.candidates,
                requirements=effect_uptime_requirements,
                passives=tuple(passives),
                character_id=character_id,
            )
            effect_map = effect_evidence.assessments_by_candidate

        evaluated = self.evaluation_service.evaluate(
            build=build,
            baseline_plan=seed_plan,
            baseline_sustain=seed_sustain,
            candidates=neighborhood.candidates,
            context=evaluation_context,
        )
        ranking = self.evaluation_service.rank(
            evaluated,
            effect_uptime_assessments_by_candidate=effect_map,
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
            effect_evidence=effect_evidence,
        )


__all__ = [
    "RotationSupportCadenceProgressionService",
    "RotationSupportCadenceProgressionStep",
]
