from __future__ import annotations

from collections.abc import Iterable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RecoveryRuntimeActivationAnchorResolverFactory,
    RecoveryRuntimeCombatStateResolverFactory,
    RotationRecoveryHeavyCandidateOrchestrationResult,
    RotationRecoveryHeavyCandidateOrchestrationService,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalRoleAwareInputResolver,
    RecoveryFinalScorecardResolver,
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RecoveryDisplayedRecoveryResolverFactory,
    RecoveryMaximumEventResolver,
    RecoveryRestorationResolverFactory,
)


class RotationRecoveryHeavyCandidateWorkflowService:
    """Compose recovery stabilization with canonical final-family evaluation.

    Static calculation context and optional per-plan resource ceiling/recovery
    evidence stay explicit through this boundary. The workflow does not infer them
    from role or build labels; callers that have canonical evidence may provide it,
    while legacy callers retain the historical static-resource behavior.

    Optional runtime resolvers are bound only after each candidate stabilizes, so
    final-family scorecards always query the actual final plan rather than stale
    seed-plan timing. Heavy restoration can likewise be provided as a plan-aware
    resolver factory so each regenerated plan is replayed against matching evidence.

    Effect-aware callers may additionally provide final stabilized role evidence.
    When supplied, required-effect uptime remains a hard gate and the surviving
    candidates are then ordered through the canonical role-aware ranker. Callers that
    omit role evidence retain the historical effect-only final-family evaluation.
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
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
        runtime_combat_state_resolver_factory: RecoveryRuntimeCombatStateResolverFactory | None = None,
        runtime_activation_anchor_resolver_factory: RecoveryRuntimeActivationAnchorResolverFactory | None = None,
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
            restoration_resolver_factory=restoration_resolver_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            runtime_combat_state_resolver_factory=runtime_combat_state_resolver_factory,
            runtime_activation_anchor_resolver_factory=runtime_activation_anchor_resolver_factory,
        )

    def run_effects(
        self,
        *,
        player_build: PlayerBuild,
        character_build: CharacterBuild,
        candidates: tuple[RecoveryHeavyCandidateOrchestrationInput, ...],
        scorecard_resolver: RecoveryFinalScorecardResolver,
        role_aware_input_resolver: RecoveryFinalRoleAwareInputResolver | None = None,
        requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
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
        runtime_combat_state_resolver_factory: RecoveryRuntimeCombatStateResolverFactory | None = None,
        runtime_activation_anchor_resolver_factory: RecoveryRuntimeActivationAnchorResolverFactory | None = None,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        if role_aware_input_resolver is None:
            final_evaluator = self.final_family_service.effect_evaluator(
                build=character_build,
                scorecard_resolver=scorecard_resolver,
                requirements=tuple(requirements),
                passives=tuple(passives),
            )
        else:
            final_evaluator = self.final_family_service.effect_role_aware_evaluator(
                build=character_build,
                input_resolver=role_aware_input_resolver,
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
            restoration_resolver_factory=restoration_resolver_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            runtime_combat_state_resolver_factory=runtime_combat_state_resolver_factory,
            runtime_activation_anchor_resolver_factory=runtime_activation_anchor_resolver_factory,
        )


__all__ = ["RotationRecoveryHeavyCandidateWorkflowService"]
