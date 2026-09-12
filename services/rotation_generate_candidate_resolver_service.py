from __future__ import annotations

from dataclasses import dataclass

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateSharedEvaluationContext,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecard,
    RotationCandidateScorecardService,
)
from services.rotation_duration_analysis_service import RotationDurationAnalysisService
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RecoveryCandidateEvaluatorResolver,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
)
from services.rotation_sustain_service import RotationSustainProjection, RotationSustainService


@dataclass(frozen=True)
class RotationGenerateCandidateResolvers:
    """Canonical evaluator/scorecard functions for one Generate candidate family."""

    evaluator_resolver: RecoveryCandidateEvaluatorResolver
    scorecard_resolver: RecoveryFinalScorecardResolver
    baseline_sustain: RotationSustainProjection


class RotationGenerateCandidateResolverService:
    """Compose Generate-time candidate resolvers from existing canonical services.

    This service owns no ESO formulas and no encounter policy. It evaluates the exact
    generated seed plan once through ``RotationSustainService`` and then reuses
    ``RotationCandidateScorecardService`` plus ``RotationCandidateRankingService`` for
    both recovery fixed-point hard-obligation checks and final-family scorecards.

    The baseline remains the exact seed plan that entered canonical candidate
    generation. Candidate sustain comes from each recovery replay's final projection,
    so Heavy Attack restoration and other replayed resource evidence are not
    recalculated or approximated here. Explicit encounter obligations are accepted
    only through ``RotationCandidateSharedEvaluationContext``.
    """

    def __init__(
        self,
        *,
        sustain_service: RotationSustainService | None = None,
        scorecard_service: RotationCandidateScorecardService | None = None,
        ranking_service: RotationCandidateRankingService | None = None,
        duration_service: RotationDurationAnalysisService | None = None,
    ) -> None:
        self.sustain_service = sustain_service or RotationSustainService()
        self.scorecard_service = scorecard_service or RotationCandidateScorecardService()
        self.ranking_service = ranking_service or RotationCandidateRankingService()
        self.duration_service = duration_service or RotationDurationAnalysisService()

    def build(
        self,
        *,
        player_build: PlayerBuild,
        baseline_plan: RotationPlan,
        resource: ResourceType,
        context: RotationCandidateSharedEvaluationContext | None = None,
    ) -> RotationGenerateCandidateResolvers:
        evidence = context or RotationCandidateSharedEvaluationContext()
        baseline_sustain = self.sustain_service.evaluate(
            build=player_build,
            plan=baseline_plan,
            resource=resource,
        )

        def scorecard_for(
            plan: RotationPlan,
            sustain: RotationSustainProjection,
        ) -> RotationCandidateScorecard:
            duration = self.duration_service.analyze(plan)
            return self.scorecard_service.compare(
                baseline_plan=baseline_plan,
                candidate_plan=plan,
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
                ultimate_affordability_requirement=(
                    evidence.ultimate_affordability_requirement
                ),
                encounter_requirements=evidence.encounter_requirements,
                support_coverage=evidence.support_coverage,
                candidate_duration=duration,
                runtime_uptime_requirements=evidence.runtime_uptime_requirements,
                runtime_uptime_objective=evidence.runtime_uptime_objective,
            )

        def evaluator_resolver(candidate_id: str):
            resolved_id = str(candidate_id or "").strip()
            if not resolved_id:
                raise ValueError("rotation Generate candidate evaluator requires candidate_id")

            def evaluate(plan, replay):
                scorecard = scorecard_for(plan, replay.final_projection)
                ranked = tuple(
                    self.ranking_service.rank(
                        (
                            RotationCandidateRankingInput(
                                candidate_id=resolved_id,
                                scorecard=scorecard,
                            ),
                        )
                    )
                )
                if len(ranked) != 1:
                    raise ValueError(
                        "rotation Generate candidate evaluator expected one ranking result"
                    )
                result = ranked[0]
                if result.candidate_id.casefold() != resolved_id.casefold():
                    raise ValueError(
                        "rotation Generate candidate evaluator changed candidate_id: "
                        f"expected {resolved_id!r}, got {result.candidate_id!r}"
                    )
                return result

            return evaluate

        def scorecard_resolver(snapshot):
            return scorecard_for(snapshot.plan, snapshot.replay.final_projection)

        return RotationGenerateCandidateResolvers(
            evaluator_resolver=evaluator_resolver,
            scorecard_resolver=scorecard_resolver,
            baseline_sustain=baseline_sustain,
        )


__all__ = [
    "RotationGenerateCandidateResolverService",
    "RotationGenerateCandidateResolvers",
]
