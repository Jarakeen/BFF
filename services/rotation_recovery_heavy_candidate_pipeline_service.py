from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import Callable

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
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
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
    RecoveryFinalRoleAwareInputResolver,
    RecoveryFinalScorecardResolver,
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
from services.rotation_saved_build_bar_access_service import (
    RotationSavedBuildBarAccessService,
)


RecoveryHeavyCompletionEvidenceFactory = Callable[
    [RotationPlan],
    tuple[RotationHeavyAttackCompletionEvidence, ...],
]


class RotationRecoveryHeavyCandidatePipelineService:
    """Compose candidate-policy generation with the recovery-aware family workflow.

    Canonical callers may carry an already-resolved static calculation context plus
    per-plan resource-maximum, displayed-recovery, heavy-restoration, and time-varying
    combat-state resolvers through the complete candidate pipeline. Those inputs stay
    explicit so legacy callers do not acquire invented mechanics.

    Effect-aware callers may instead supply plan-specific Heavy Attack completion
    evidence. The pipeline then builds the restoration resolver for each regenerated
    plan through ``RotationHeavySustainProjectionService`` so callers provide reviewed
    evidence rather than reimplementing weapon, progression, or restore math.

    When no explicit restoration source is supplied, effect-aware evaluation uses the
    same duration-aware scheduler provenance already carried by each regenerated plan.
    Only reviewed 1.8-second Heavy Attack reservations become completion evidence;
    an unreserved/manual heavy therefore still fails closed rather than receiving an
    invented restore.

    Final scorecards are additionally decorated with saved-build bar-access rules.
    This keeps ESO gear mechanics such as Oakensoul outside generic plan semantics
    while ensuring both generic and effect-aware candidate workflows reject an
    otherwise well-formed plan that the equipped build cannot execute. When final
    role-aware evidence is supplied, its scorecard is replaced with that same
    decorated canonical scorecard before role policy is allowed to rank the family.
    """

    def __init__(
        self,
        *,
        generation_bridge: RotationRecoveryHeavyCandidateGenerationBridgeService | None = None,
        workflow: RotationRecoveryHeavyCandidateWorkflowService | None = None,
        active_bar_assessor: RotationActiveBarAssessor | None = None,
        heavy_sustain_service: RotationHeavySustainProjectionService | None = None,
    ) -> None:
        self.generation_bridge = (
            generation_bridge or RotationRecoveryHeavyCandidateGenerationBridgeService()
        )
        self.workflow = workflow or RotationRecoveryHeavyCandidateWorkflowService()
        self.active_bar_assessor = active_bar_assessor or RotationActiveBarAssessor()
        self.heavy_sustain_service = (
            heavy_sustain_service or RotationHeavySustainProjectionService()
        )

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

    @staticmethod
    def _with_canonical_role_scorecard(
        resolver: RecoveryFinalRoleAwareInputResolver,
        scorecard_resolver: RecoveryFinalScorecardResolver,
    ) -> RecoveryFinalRoleAwareInputResolver:
        def resolve(snapshot):
            role_input = resolver(snapshot)
            return replace(role_input, scorecard=scorecard_resolver(snapshot))

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
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
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
            restoration_resolver_factory=restoration_resolver_factory,
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
        role_aware_input_resolver: RecoveryFinalRoleAwareInputResolver | None = None,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
        completion_evidence_factory: RecoveryHeavyCompletionEvidenceFactory | None = None,
        initial_bar: str = "front",
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

        active_restoration_resolver = restoration_resolver
        active_restoration_factory = restoration_resolver_factory
        active_completion_factory = completion_evidence_factory
        if (
            active_completion_factory is None
            and restoration_resolver is None
            and restoration_resolver_factory is None
        ):
            active_completion_factory = (
                self.heavy_sustain_service
                .completion_evidence_from_verified_reservations
            )

        if active_completion_factory is not None:
            if restoration_resolver is not None or restoration_resolver_factory is not None:
                raise ValueError(
                    "completion_evidence_factory cannot be combined with an explicit "
                    "heavy restoration resolver or resolver factory"
                )

            def canonical_restoration_factory(
                plan: RotationPlan,
            ) -> VerifiedRecoveryHeavyRestorationResolver:
                completion_evidence = tuple(active_completion_factory(plan))
                return self.heavy_sustain_service.restoration_resolver_for_plan(
                    character_build=character_build,
                    sustain_build=player_build,
                    plan=plan,
                    resource=resource,
                    initial_bar=initial_bar,
                    completion_evidence=completion_evidence,
                )

            active_restoration_factory = canonical_restoration_factory

        final_scorecard_resolver = self._with_saved_build_bar_access(
            player_build,
            scorecard_resolver,
        )
        active_role_input_resolver = (
            None
            if role_aware_input_resolver is None
            else self._with_canonical_role_scorecard(
                role_aware_input_resolver,
                final_scorecard_resolver,
            )
        )

        return self.workflow.run_effects(
            player_build=player_build,
            character_build=character_build,
            candidates=bridged.candidates,
            scorecard_resolver=final_scorecard_resolver,
            role_aware_input_resolver=active_role_input_resolver,
            requirements=requirement_tuple,
            passives=passive_tuple,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver=active_restoration_resolver,
            restoration_resolver_factory=active_restoration_factory,
            reserve_assessment_resolver=reserve_assessment_resolver,
            max_iterations=max_iterations,
            calculation_context=calculation_context,
            maximum_event_resolver=maximum_event_resolver,
            displayed_recovery_resolver_factory=displayed_recovery_resolver_factory,
            runtime_combat_state_resolver_factory=runtime_combat_state_resolver_factory,
        )


__all__ = [
    "RecoveryHeavyCompletionEvidenceFactory",
    "RotationRecoveryHeavyCandidatePipelineService",
]
