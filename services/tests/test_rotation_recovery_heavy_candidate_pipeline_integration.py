from __future__ import annotations

from types import SimpleNamespace

from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import (
    RotationCandidateGenerationService,
    RotationRefreshLeadCandidateOption,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
)
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecard,
    RotationDemandActionRequirement,
    RotationDemandCoverageEvidence,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_recovery_heavy_candidate_generation_bridge_service import (
    RotationRecoveryHeavyCandidateGenerationBridgeService,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RotationRecoveryHeavyCandidateOrchestrationService,
)
from services.rotation_recovery_heavy_candidate_pipeline_service import (
    RotationRecoveryHeavyCandidatePipelineService,
)
from services.rotation_recovery_heavy_candidate_stabilization_service import (
    RotationRecoveryHeavyCandidateStabilizationService,
)
from services.rotation_recovery_heavy_candidate_workflow_service import (
    RotationRecoveryHeavyCandidateWorkflowService,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationService,
)


_SUPPORT_DEMAND = RotationDemandWindow(
    name="Required Support Window",
    start_seconds=4.0,
    end_seconds=6.0,
    kind=RotationDemandKind.SUPPORT,
    pattern=RotationDemandPattern.BURST,
)
_SUPPORT_REQUIREMENT = RotationDemandActionRequirement(
    demand_name=_SUPPORT_DEMAND.name,
    skill_name="Required Support",
    bar="front",
)


class _ControlledRefinementService:
    """Deterministic policy fixture around the real candidate-generation bridge.

    The baseline is already sustainable and keeps the support cast. The explicit
    recovery-risk option has a high-cost action. Once recovery pressure exists it
    replaces the support cast with a heavy attack, modelling the exact failure this
    integration test needs to prove the pipeline rejects.
    """

    def refine(
        self,
        plan,
        *,
        priorities=None,
        wait_decision=None,
        demands=(),
        demand_refresh_leads=(),
        demand_action_claims=(),
    ):
        risky = bool(tuple(demand_refresh_leads))
        pressured = bool(getattr(wait_decision, "has_pressure", False))
        actions = [
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="High Cost Action" if risky else "Stable Recovery Action",
                bar="front",
            )
        ]
        actions.append(
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=(
                    RotationActionKind.HEAVY_ATTACK
                    if risky and pressured
                    else RotationActionKind.SKILL
                ),
                name=("Heavy Attack" if risky and pressured else "Required Support"),
                bar="front",
            )
        )
        return SimpleNamespace(
            plan=RotationPlan(
                character_name=plan.character_name,
                build_name=plan.build_name,
                duration_seconds=plan.duration_seconds,
                actions=tuple(actions),
            )
        )


class _ControlledReplayService:
    """Controlled resource evidence while the real fixed-point service stays live."""

    @staticmethod
    def replay(
        *,
        build,
        plan,
        resource,
        restoration_resolver,
        maximum_events=(),
        calculation_context=None,
        displayed_recovery_at=None,
    ):
        risky = any(action.name == "High Cost Action" for action in plan.actions)
        has_heavy = any(
            action.kind is RotationActionKind.HEAVY_ATTACK for action in plan.actions
        )
        shortfall = 500 if risky and not has_heavy else 0
        ending = 6500 if has_heavy else 2500
        timeline = SimpleNamespace(
            resource=resource,
            starting_amount=2500,
            ending_amount=ending,
            events=(),
            total_shortfall=shortfall,
        )
        projection = SimpleNamespace(run=SimpleNamespace(timeline=timeline))
        return SimpleNamespace(
            initial_projection=projection,
            final_projection=projection,
            restoration_events=(),
            steps=(),
        )

    @staticmethod
    def pressure_resolver(
        *,
        replay,
        maximum_amount,
        trigger_fraction,
        reserve_assessment_resolver=None,
    ):
        def resolve(context):
            return SimpleNamespace(
                recommended=True,
                current_amount=replay.final_projection.run.timeline.ending_amount,
                maximum_amount=maximum_amount,
                trigger_fraction=trigger_fraction,
                time_seconds=context.time_seconds,
            )

        return resolve


def _neutral_consequence() -> RotationPlanConsequence:
    return RotationPlanConsequence(
        resource_kind=RotationResourceConsequenceKind.NEUTRAL,
        cast_deltas=(),
        cost_deltas=(),
        total_cost_delta=0,
        minimum_resource_delta=0,
        ending_resource_delta=0,
        shortfall_delta=0,
        wait_delta=0,
    )


def _scorecard(plan: RotationPlan, replay) -> RotationCandidateScorecard:
    cast_times = tuple(
        float(action.time_seconds)
        for action in plan.actions
        if action.kind is RotationActionKind.SKILL
        and action.name == _SUPPORT_REQUIREMENT.skill_name
        and action.bar == _SUPPORT_REQUIREMENT.bar
        and _SUPPORT_DEMAND.start_seconds
        <= float(action.time_seconds)
        < _SUPPORT_DEMAND.end_seconds
    )
    coverage = RotationDemandCoverageEvidence(
        requirement=_SUPPORT_REQUIREMENT,
        demand=_SUPPORT_DEMAND,
        observed_casts=len(cast_times),
        cast_times=cast_times,
    )
    return RotationCandidateScorecard(
        consequence=_neutral_consequence(),
        demand_coverage=(coverage,),
        missing_required_effects=(),
        candidate_shortfall=int(
            replay.final_projection.run.timeline.total_shortfall
        ),
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def test_recovery_pipeline_rejects_sustain_fix_that_displaces_hard_support_obligation() -> None:
    generation = RotationCandidateGenerationService(_ControlledRefinementService())
    bridge = RotationRecoveryHeavyCandidateGenerationBridgeService(
        generation_service=generation
    )
    fixed_point = RotationRecoveryHeavyStabilizationService(
        replay_service=_ControlledReplayService()
    )
    candidate_stabilization = RotationRecoveryHeavyCandidateStabilizationService(
        stabilization_service=fixed_point
    )
    orchestration = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=candidate_stabilization
    )
    workflow = RotationRecoveryHeavyCandidateWorkflowService(
        orchestration_service=orchestration
    )
    pipeline = RotationRecoveryHeavyCandidatePipelineService(
        generation_bridge=bridge,
        workflow=workflow,
    )
    ranker = RotationCandidateRankingService()

    build = PlayerBuild(
        Name="Integration Character",
        BuildName="Recovery Gate",
        Role="Support",
    )
    seed = RotationPlan(
        character_name=build.Name,
        build_name=build.BuildName,
        duration_seconds=10.0,
        actions=(),
    )
    priorities = AbilityPriorityList(
        character_name=build.Name,
        build_name=build.BuildName,
        role=build.Role,
        entries=(),
    )

    def evaluator_resolver(candidate_id: str):
        def evaluate(plan, replay):
            return ranker.rank(
                (
                    RotationCandidateRankingInput(
                        candidate_id=candidate_id,
                        scorecard=_scorecard(plan, replay),
                    ),
                )
            )[0]

        return evaluate

    result = pipeline.run_generic(
        player_build=build,
        seed_plan=seed,
        priorities=priorities,
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=lambda snapshot: _scorecard(snapshot.plan, snapshot.replay),
        resource=ResourceType.MAGICKA,
        maximum_amount=10_000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        demands=(_SUPPORT_DEMAND,),
        options=(
            RotationRefreshLeadCandidateOption(
                option_id="recovery-heavy-risk",
                refresh_leads=(
                    DemandRefreshLead(
                        demand_name=_SUPPORT_DEMAND.name,
                        bar="front",
                        skill_name="Required Support",
                        lead_seconds=1.0,
                    ),
                ),
            ),
        ),
        wait_decision_factory=lambda candidate_id, pressure: SimpleNamespace(
            candidate_id=candidate_id,
            has_pressure=pressure is not None,
        ),
        max_iterations=5,
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.evaluation.candidate_id == "baseline"
    assert result.selected_candidate.selectable is True

    by_id = {item.candidate_id: item for item in result.stabilized_candidates}
    baseline = by_id["baseline"]
    risky = by_id["recovery-heavy-risk"]

    assert baseline.stabilization.termination_reason == "stable_fixed_point"
    assert baseline.stabilization.tracked_hard_obligations_satisfied is True

    assert risky.stabilization.termination_reason == "stable_no_legal_improvement"
    assert risky.stabilization.tracked_hard_obligations_satisfied is False
    assert risky.replay.final_projection.run.timeline.total_shortfall == 0
    assert any(
        action.kind is RotationActionKind.HEAVY_ATTACK
        for action in risky.plan.actions
    )
    assert not any(
        action.kind is RotationActionKind.SKILL
        and action.name == "Required Support"
        for action in risky.plan.actions
    )

    ranked_by_id = {
        item.evaluation.candidate_id: item for item in result.ranked_candidates
    }
    assert ranked_by_id["baseline"].selectable is True
    assert ranked_by_id["recovery-heavy-risk"].selectable is False
    assert any(
        "missing 1 explicit demand requirement" in reason
        for reason in ranked_by_id["recovery-heavy-risk"].evaluation.reasons
    )
