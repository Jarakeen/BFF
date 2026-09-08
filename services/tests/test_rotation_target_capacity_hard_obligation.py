from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_target_capacity import RotationTargetCapacityRequirement
from services.rotation_candidate_hard_obligation_state_service import (
    RotationCandidateHardObligationStateService,
)
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)
from services.rotation_target_capacity_ranking_service import (
    RotationTargetCapacityRankingService,
)
from services.rotation_target_capacity_scorecard_service import (
    RotationTargetCapacityScorecardService,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                10.0,
                0,
                RotationActionKind.SKILL,
                "Limited Heal",
                "front",
            ),
        ),
    )


def _sustain():
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=30000,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            timeline=timeline,
            action_cost_events=(),
        ),
        unresolved=(),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Raid burst",
        start_seconds=9.0,
        end_seconds=12.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _scorecard(maximum_targets: int):
    plan = _plan()
    base = RotationCandidateScorecardService().compare(
        baseline_plan=plan,
        candidate_plan=plan,
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
    )
    return RotationTargetCapacityScorecardService().apply(
        base,
        plan=plan,
        demands=(_demand(),),
        requirements=(
            RotationTargetCapacityRequirement(
                demand_name="Raid burst",
                maximum_targets=maximum_targets,
                action_name="Limited Heal",
                action_kind=RotationActionKind.SKILL,
                bar="front",
            ),
        ),
    )


def test_target_capacity_shortfall_is_known_scorecard_hard_failure() -> None:
    scorecard = _scorecard(6)

    assert len(scorecard.target_capacity_violations) == 1
    assert scorecard.target_capacity_violations[0].shortfall == 6
    assert not scorecard.supplied_obligations_satisfied
    assert scorecard.candidate_specific_unresolved == ()


def test_target_capacity_shortfall_ranks_ineligible_with_explicit_reason() -> None:
    legal = _scorecard(12)
    illegal = _scorecard(6)

    ranked = RotationTargetCapacityRankingService().rank(
        (
            RotationCandidateRankingInput("illegal", illegal),
            RotationCandidateRankingInput("legal", legal),
        )
    )

    assert ranked[0].candidate_id == "legal"
    assert ranked[0].tier is RotationCandidateTier.ELIGIBLE
    assert ranked[1].tier is RotationCandidateTier.INELIGIBLE
    assert any("1 target-capacity violation" in reason for reason in ranked[1].reasons)
    assert any(
        "cap 6, demand 12, shortfall 6" in reason
        for reason in ranked[1].reasons
    )


def test_target_capacity_shortfall_participates_in_fixed_point_hard_state() -> None:
    scorecard = _scorecard(6)

    state = RotationCandidateHardObligationStateService().from_scorecard(scorecard)

    assert any(
        token.startswith(
            "target_capacity|Raid burst|Limited Heal|skill|front|10|6|12|6"
        )
        for token in state
    )


def test_final_family_default_rankers_share_target_capacity_awareness() -> None:
    service = RotationRecoveryHeavyFinalFamilyEvaluationService()

    assert isinstance(service.base_ranker, RotationTargetCapacityRankingService)
    assert service.effect_ranker.base_ranker is service.base_ranker
