from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_ultimate_affordability import RotationUltimateAffordabilityRequirement
from minmax.ultimate_resource_timeline import UltimateSpendRule
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from ui.rotation_ultimate_affordability_candidate_support import (
    RotationUltimateAffordabilityCandidateSupport,
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


def _scorecard(_snapshot) -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=_consequence(),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


class _Delegate:
    def __init__(self, plan: RotationPlan) -> None:
        self.plan = plan
        self.scorecard = None
        self.calls = []

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        snapshot = SimpleNamespace(candidate_id="ultimate-candidate", plan=self.plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        return SimpleNamespace(scorecard=self.scorecard)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                10.0,
                0,
                RotationActionKind.ULTIMATE,
                "Aggressive Horn",
                "front",
            ),
        ),
    )


def test_wrapper_attaches_final_plan_ultimate_affordability_hard_failure() -> None:
    delegate = _Delegate(_plan())
    support = RotationUltimateAffordabilityCandidateSupport(
        canonical_candidates=delegate,
    )

    support.run_effects(
        scorecard_resolver=_scorecard,
        ultimate_affordability_requirement=RotationUltimateAffordabilityRequirement(
            starting_amount=50.0,
            spend_rules=(UltimateSpendRule("Aggressive Horn", 250.0),),
        ),
    )

    assert delegate.scorecard is not None
    assert len(delegate.scorecard.ultimate_affordability_violations) == 1
    assert delegate.scorecard.supplied_obligations_satisfied is False
    assert delegate.scorecard.candidate_specific_unresolved == ()


def test_wrapper_preserves_existing_path_when_no_ultimate_evidence_is_supplied() -> None:
    delegate = _Delegate(_plan())
    support = RotationUltimateAffordabilityCandidateSupport(
        canonical_candidates=delegate,
    )

    support.run_effects(scorecard_resolver=_scorecard)

    assert delegate.scorecard is not None
    assert delegate.scorecard.ultimate_affordability_assessment is None
    assert delegate.scorecard.supplied_obligations_satisfied is True
