from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.passive_grant import PassiveGrant
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import RotationRefreshLeadCandidateOption
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RecoveryCandidateEvaluatorResolver,
    RecoveryPressureWaitDecisionFactory,
    RotationRecoveryHeavyCandidateGenerationBridgeService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryRuntimeCombatStateResolverFactory,
    RotationRecoveryHeavyCandidateOrchestrationResult,
)
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RecoveryFinalScorecardResolver,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RecoveryDisplayedRecoveryResolverFactory,
    RecoveryMaximumEventResolver,
)
from services.rotation_saved_build_bar_access_service import (
    RotationSavedBuildBarAccessService,
)


class RotationRecoveryHeavyCandidatePipelineService:
    """Compose candidate-policy generation with the recovery-aware family workflow.

    Canonical callers may carry an already-resolved static calculation context plus
    per-plan resource-maximum, displayed-recovery, and time-varying combat-state
    resolvers through the complete candidate pipeline. Those inputs remain explicit
    and optional so legacy callers do not acquire invented mechanics.

    Final scorecards are additionally decorated with saved-build bar-access rules.
    This keeps ESO gear mechanics such as Oakensoul outside generic plan semantics
    while ensuring both generic and effect-aware candidate workflows reject an
    otherwise well-formed plan that the equipped build cannot execute.
    """

    def __init__(
        self,
        *,
        generation_bridge: RotationRecoveryHeavyCandidateGenerationBridgeService | None = None,
        workflow: RotationRecoveryHeavyCandidateWorkflowService | None = None,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
    ) -> None:
        self.generation_bridge = (
            generation_bridge or RotationRecoveryHeavyCandidateGenerationBridgeService()
        )
        self.workflow = workflow or RotationRecoveryHeavyCandidateWorkflowService()
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()

    def _with_saved_build_bar_access(
        self,
        player_build: PlayerBuild,
        resolver: RecoveryFinalScorecardResolver,
    ) -> RecoveryFinalScorecardResolver:
        def resolve(snapshot):
            scorecard = resolver(snapshot)
            base = scorecard.active_bar_assessment
            if base is None:
                base = self.active_bar_assessor.assess(snapshot.plan, initial_bar="front")
            restricted = RotationSavedBuildBarAccessService.restrict(
                player_build,
                snapshot.plan,
                base,
            )
            if restricted == scorecard.active_bar_assessment:
                return scorecard
            return replace(scorecard, active_bar_assessment=restricted)

        return resolve

    def run_generic(
        self,
        *,
        player_build: PlayerBuild,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
        runtime_combat_state_resolver_factory: RecoveryRuntimeCombatStateResolverFactory | None = None,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        demand_tuple = tuple(demands)
        option_tuple = tuple(options)
        bridged = self.generation_bridge.build(
            seed_plan=seed_plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            demands=demand_tuple,
            options=option_tuple,
            wait_decision_factory=wait_decision_factory,
            baseline_id=baseline_id,
        )
        return self.workflow.run_generic(
            player_build=player_build,
            candidates=bridged.candidates,
            scorecard_resolver=self._with_saved_build_bar_access(
                player_build,
                scorecard_resolver,
            ),
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            runtime_combat_state_resolver_factory=runtime_combat_state_resolver_factory,
        )

    def run_effects(
        self,
        *,
        player_build: PlayerBuild,
        character_build: CharacterBuild,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        evaluator_resolver: RecoveryCandidateEvaluatorResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        demands: Iterable[RotationDemandWindow] = (),
        options: Iterable[RotationRefreshLeadCandidateOption] = (),
        wait_decision_factory: RecoveryPressureWaitDecisionFactory | None = None,
        requirements: Iterable[RotationEffectUptimeRequirement] = (),
        passives: Iterable[PassiveGrant] = (),
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        max_iterations: int = 6,
        baseline_id: str = "baseline",
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
        runtime_combat_state_resolver_factory: RecoveryRuntimeCombatStateResolverFactory | None = None,
    ) -> RotationRecoveryHeavyCandidateOrchestrationResult:
        demand_tuple = tuple(demands)
        option_tuple = tuple(options)
        requirement_tuple = tuple(requirements)
        passive_tuple = tuple(passives)
        bridged = self.generation_bridge.build(
            seed_plan=seed_plan,
            priorities=priorities,
            evaluator_resolver=evaluator_resolver,
            demands=demand_tuple,
            options=option_tuple,
            wait_decision_factory=wait_decision_factory,
            baseline_id=baseline_id,
        )
        return self.workflow.run_effects(
            player_build=player_build,
            character_build=character_build,
            candidates=bridged.candidates,
            scorecard_resolver=self._with_saved_build_bar_access(
                player_build,
                scorecard_resolver,
            ),
            requirements=requirement_tuple,
            passives=passive_tuple,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=restoration_resolver,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            runtime_combat_state_resolver_factory=runtime_combat_state_resolver_factory,
        )


__all__ = ["RotationRecoveryHeavyCandidatePipelineService"]
