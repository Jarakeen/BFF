from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.gear_piece import ArmorPiece, GearSlot
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.rotation_candidate_effect_obligation_service import (
    RotationCandidateEffectObligationService,
    RotationEffectObligationCandidate,
)
from services.rotation_candidate_generation_service import RotationCandidateGenerationService
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_effect_uptime_service import (
    RotationEffectUptimeRequirement,
    RotationEffectUptimeService,
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


class _EffectRefinementService:
    def refine(
        self,
        plan,
        *,
        priorities=None,
        wait_decision=None,
        demands=(),
        demand_refresh_leads=(),
    ):
        return SimpleNamespace(
            plan=RotationPlan(
                character_name=plan.character_name,
                build_name=plan.build_name,
                duration_seconds=40.0,
                actions=(
                    RotationAction(
                        time_seconds=0.0,
                        sequence=0,
                        kind=RotationActionKind.SKILL,
                        name="Winter's Revenge",
                        bar="front",
                    ),
                    RotationAction(
                        time_seconds=20.0,
                        sequence=0,
                        kind=RotationActionKind.SKILL,
                        name="Winter's Revenge",
                        bar="front",
                    ),
                ),
            )
        )


class _StableReplayService:
    @staticmethod
    def replay(*, build, plan, resource, restoration_resolver):
        timeline = SimpleNamespace(
            resource=resource,
            starting_amount=30_000,
            ending_amount=30_000,
            events=(),
            total_shortfall=0,
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
                recommended=False,
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


def _scorecard() -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_neutral_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _character_build() -> CharacterBuild:
    chilled = EffectVariant(
        name="chilled",
        layer=EffectLayer.CAST,
        source="Winter's Revenge",
        duration=4.0,
        category=SupportEffectCategory.STATUS,
        target_type=SupportTargetType.ENEMY,
    )
    winter = SlottedSkill(
        skill_id="winters_revenge",
        skill_line_id="winters_embrace",
        is_cast=True,
        effects=(chilled,),
    )
    duration_modifier = EffectVariant(
        name="status_effect_duration_increase",
        layer=EffectLayer.PASSIVE,
        source="Serpent's Disdain (5)",
        magnitude=16.0,
        category=SupportEffectCategory.OTHER,
        target_type=SupportTargetType.SELF,
    )
    return CharacterBuild(
        name="Effect Recovery Integration",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FROST_STAFF),
            off_hand=None,
            slots=(winter,),
        ),
        armor=(
            ArmorPiece(
                slot=GearSlot.CHEST,
                effects=(duration_modifier,),
            ),
        ),
    )


def test_effect_pipeline_preserves_build_duration_modifier_through_fixed_point_and_final_selection() -> None:
    generation = RotationCandidateGenerationService(_EffectRefinementService())
    bridge = RotationRecoveryHeavyCandidateGenerationBridgeService(
        generation_service=generation
    )
    fixed_point = RotationRecoveryHeavyStabilizationService(
        replay_service=_StableReplayService()
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

    player_build = PlayerBuild(
        Name="Integration Character",
        BuildName="Effect Recovery Integration",
        Role="Healer",
    )
    character_build = _character_build()
    seed = RotationPlan(
        character_name=player_build.Name,
        build_name=player_build.BuildName,
        duration_seconds=40.0,
        actions=(),
    )
    priorities = AbilityPriorityList(
        character_name=player_build.Name,
        build_name=player_build.BuildName,
        role=player_build.Role,
        entries=(),
    )
    requirement = RotationEffectUptimeRequirement(
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        minimum_uptime=0.90,
        bar="front",
    )
    effect_uptime = RotationEffectUptimeService()
    base_ranker = RotationCandidateRankingService()
    effect_ranker = RotationCandidateEffectObligationService()

    def evaluator_resolver(candidate_id: str):
        def evaluate(plan, replay):
            assessments = effect_uptime.assess(
                plan=plan,
                build=character_build,
                requirements=(requirement,),
            )
            return effect_ranker.rank(
                (
                    RotationEffectObligationCandidate(
                        ranking_input=RotationCandidateRankingInput(
                            candidate_id=candidate_id,
                            scorecard=_scorecard(),
                        ),
                        effect_uptime_assessments=assessments,
                    ),
                )
            )[0]

        return evaluate

    result = pipeline.run_effects(
        player_build=player_build,
        character_build=character_build,
        seed_plan=seed,
        priorities=priorities,
        evaluator_resolver=evaluator_resolver,
        scorecard_resolver=lambda snapshot: _scorecard(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.30,
        restoration_resolver=lambda heavy: None,
        requirements=(requirement,),
        max_iterations=4,
    )

    assert result.selected_candidate is not None
    assert result.selected_candidate.candidate_id == "baseline"
    assert result.selected_candidate.selectable is True
    assert result.selected_candidate.evaluation.tier is RotationCandidateTier.ELIGIBLE

    stabilized = result.stabilized_candidates[0]
    assert stabilized.stabilization.termination_reason == "stable_fixed_point"
    assert stabilized.stabilization.tracked_hard_obligations_satisfied is True
    assert all(
        not iteration.hard_obligation_state
        for iteration in stabilized.stabilization.iterations
    )

    assessment = result.selected_candidate.evaluation.effect_uptime_assessments[0]
    assert assessment.summary is not None
    assert assessment.summary.base_duration_seconds == pytest.approx(4.0)
    assert assessment.summary.effective_duration_seconds == pytest.approx(20.0)
    assert assessment.summary.uptime_fraction == pytest.approx(1.0)
    assert assessment.summary.applied_modifier_sources == ("Serpent's Disdain (5)",)

    without_modifier = RotationEffectUptimeService().assess(
        plan=stabilized.plan,
        build=CharacterBuild(
            name="No Duration Modifier",
            character_class=CharacterClass.WARDEN,
            role=Role.HEALER,
            front_bar=character_build.front_bar,
        ),
        requirements=(requirement,),
    )[0]
    assert without_modifier.observed_uptime == pytest.approx(0.20)
    assert without_modifier.satisfied is False
