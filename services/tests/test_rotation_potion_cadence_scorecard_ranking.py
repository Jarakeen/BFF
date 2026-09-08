from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from services.rotation_candidate_ranking_service import (
    RotationCandidateRankingInput,
    RotationCandidateRankingService,
    RotationCandidateTier,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_potion_cadence_cooldown_bridge_service import (
    RotationPotionCadenceCooldownBridgeService,
)


def _consequence() -> RotationPlanConsequence:
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


def test_shared_potion_cadence_is_hard_cooldown_ranking_failure() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.POTION, "Essence of Spell Power"),
            RotationAction(30.0, 0, RotationActionKind.POTION, "Essence of Health"),
        ),
    )
    cooldown_assessment = RotationPotionCadenceCooldownBridgeService().assess(
        plan,
        RotationPotionCadenceRequirement(45.0),
    )
    scorecard = RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
        cooldown_assessment=cooldown_assessment,
    )

    ranked = RotationCandidateRankingService().rank(
        (RotationCandidateRankingInput("too-fast-potions", scorecard),)
    )

    assert ranked[0].tier is RotationCandidateTier.INELIGIBLE
    assert any("1 action cooldown violation" in reason for reason in ranked[0].reasons)
    assert any(
        "cooldown legality for 'Essence of Health'" in reason
        and "interval 30s, required 45s" in reason
        for reason in ranked[0].reasons
    )
