from __future__ import annotations

from collections.abc import Iterable

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RotationRecoveryHeavyCandidateOrchestrationResult,
    RotationRecoveryHeavyCandidateOrchestrationService,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)


class RotationRecoveryHeavyCandidateWorkflowService:
    """Compose recovery stabilization with canonical final-family evaluation.

    This is the executable service boundary for the recovery-aware candidate family
    workflow. It removes the remaining caller glue between the fixed-point
    orchestrator and the final-family evaluator while preserving their separate
    responsibilities.

    ``PlayerBuild`` remains explicit for recovery replay/stabilization and
    ``CharacterBuild`` remains explicit for build-aware effect timing. They are not
    silently converted or treated as interchangeable models. Callers that need
    effect obligations must supply both pieces of canonical build evidence.

    No encounter requirement, recovery threshold, restore amount, reserve policy,
    effect identity, uptime floor, passive, set mechanic, or strategy semantic is
    inferred here.
    """

    def __init__(
        self,
        *,
        orchestration_service: RotationRecoveryHeavyCandidateOrchestrationService | None = None,
        final_family_service: RotationRecoveryHeavyFinalFamilyEvaluationService | None = None,
    ) -> None:
        self.orchestration_service = (
            orchestration_service or RotationRecoveryHeavyCandidateOrchestrationService()
        )
        self.final_family_service = (
            final_family_service or RotationRecoveryHeavyFinalFamilyEvaluationService()
        )

    def run_generic(
        self,
        *,
        player_build: PlayerBuild,
        candidates: tuple[RecoveryHeavyCandidateOrchestrationInput, ...],
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        final_evaluator = self.final_family_service.generic_evaluator(
            scorecard_resolver=scorecard_resolver,
        )
        return self.orchestration_service.orchestrate(
            build=player_build,
            candidates=tuple(candidates),
            evaluate_final_family=final_evaluator,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
        )

    def run_effects(
        self,
        *,
        player_build: PlayerBuild,
        character_build: CharacterBuild,
        candidates: tuple[RecoveryHeavyCandidateOrchestrationInput, ...],
        scorecard_resolver: RecoveryFinalScorecardResolver,
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        final_evaluator = self.final_family_service.effect_evaluator(
            build=character_build,
            scorecard_resolver=scorecard_resolver,
            requirements=tuple(requirements),
            passives=tuple(passives),
        )
        return self.orchestration_service.orchestrate(
            build=player_build,
            candidates=tuple(candidates),
            evaluate_final_family=final_evaluator,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
        )


__all__ = ["RotationRecoveryHeavyCandidateWorkflowService"]
