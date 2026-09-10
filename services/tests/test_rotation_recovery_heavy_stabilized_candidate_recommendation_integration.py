from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_recommendation_service import (
    RotationCandidateRecommendationEvidence,
    RotationCandidateRecommendationService,
)
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_recovery_heavy_stabilized_candidate_service import (
    RotationRecoveryHeavyStabilizedCandidateService,
)


def _scorecard() -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


class _EvidenceProvider:
    def __init__(self, expected_plan: RotationPlan) -> None:
        self.expected_plan = expected_plan
        self.seen_plan = None

    def evaluate(self, *, baseline, candidate):
        self.seen_plan = candidate.plan
        assert baseline.plan is self.expected_plan
        assert candidate.plan is self.expected_plan
        return RotationCandidateRecommendationEvidence(
            candidate_id=candidate.candidate_id,
            scorecard=_scorecard(),
            role_output_value=1000.0,
            assigned_support_value=None,
            sustain_margin=5000.0,
            primary_role_displacement_seconds=0.0,
        )


def test_recommendation_consumes_the_final_fixed_point_plan() -> None:
    stable_plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                time_seconds=18.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="heavy_attack",
                bar="back",
            ),
            RotationAction(
                time_seconds=33.0,
                sequence=1,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="heavy_attack",
                bar="back",
            ),
        ),
    )
    stabilization = SimpleNamespace(
        converged=True,
        plan=stable_plan,
        replay=object(),
        iterations=(object(), object()),
        termination_reason="stable_fixed_point",
        tracked_hard_obligations_satisfied=True,
    )
    bridged = RotationRecoveryHeavyStabilizedCandidateService.from_stabilization(
        candidate_id="stable-heavy",
        stabilization=stabilization,
    )
    assert bridged.candidate is not None

    provider = _EvidenceProvider(stable_plan)
    result = RotationCandidateRecommendationService().recommend(
        candidates=(bridged.candidate,),
        evidence_provider=provider,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.plan is stable_plan
    assert result.recommended.candidate.candidate_id == "stable-heavy"
    assert provider.seen_plan is stable_plan
