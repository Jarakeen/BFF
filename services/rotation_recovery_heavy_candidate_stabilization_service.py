from __future__ import annotations

from typing import Callable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_effect_obligation_service import (
    RotationEffectObligationRankingResult,
)
from services.rotation_candidate_hard_obligation_state_service import (
    RotationCandidateHardObligationStateService,
)
from services.rotation_candidate_ranking_service import RotationCandidateRankingResult
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    RotationRecoveryHeavyReplay,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RecoveryAwareRotationGenerator,
    RecoveryDisplayedRecoveryResolverFactory,
    RecoveryMaximumEventResolver,
    RecoveryRestorationResolverFactory,
    RotationRecoveryHeavyStabilizationResult,
    RotationRecoveryHeavyStabilizationService,
)


RecoveryCandidateEvaluationResult = (
    RotationCandidateRankingResult | RotationEffectObligationRankingResult
)
RecoveryCandidateEvaluator = Callable[
    [RotationPlan, RotationRecoveryHeavyReplay],
    RecoveryCandidateEvaluationResult,
]


class RotationRecoveryHeavyCandidateStabilizationService:
    """Stabilize recovery heavies against the real candidate hard-obligation gate."""

    def __init__(
        self,
        stabilization_service: RotationRecoveryHeavyStabilizationService | None = None,
        hard_state_service: RotationCandidateHardObligationStateService | None = None,
    ) -> None:
        self.stabilization_service = (
            stabilization_service or RotationRecoveryHeavyStabilizationService()
        )
        self.hard_state_service = (
            hard_state_service or RotationCandidateHardObligationStateService()
        )

    def stabilize(
        self,
        *,
        build: PlayerBuild,
        generate: RecoveryAwareRotationGenerator,
        evaluate_candidate: RecoveryCandidateEvaluator,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
    ) -> RotationRecoveryHeavyStabilizationResult:
        def hard_state(
            plan: RotationPlan,
            replay: RotationRecoveryHeavyReplay,
        ) -> tuple[str, ...]:
            result = evaluate_candidate(plan, replay)
            if isinstance(result, RotationEffectObligationRankingResult):
                return self.hard_state_service.from_effect_ranking_result(result)
            if isinstance(result, RotationCandidateRankingResult):
                return self.hard_state_service.from_ranking_result(result)
            raise TypeError(
                "recovery candidate evaluator must return RotationCandidateRankingResult "
                "or RotationEffectObligationRankingResult"
            )

        return self.stabilization_service.stabilize(
            build=build,
            generate=generate,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            restoration_resolver_factory=restoration_resolver_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            hard_obligation_state_resolver=hard_state,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
        )


__all__ = [
    "RecoveryCandidateEvaluator",
    "RecoveryCandidateEvaluationResult",
    "RotationRecoveryHeavyCandidateStabilizationService",
]
