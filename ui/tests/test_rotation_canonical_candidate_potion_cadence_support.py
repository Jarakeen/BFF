from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=object(), unresolved=())


class _Pipeline:
    def __init__(self, final_plan: RotationPlan) -> None:
        self.final_plan = final_plan
        self.scorecard = None

    def run_effects(self, **kwargs):
        snapshot = SimpleNamespace(candidate_id="potion-candidate", plan=self.final_plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(
                candidate_id="potion-candidate",
                reasons=("all tracked hard obligations satisfied",),
            )
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        reasons = (
            ("all tracked hard obligations satisfied",)
            if selected is not None
            else ("shared potion cadence legality failed",)
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(
                SimpleNamespace(candidate_id="potion-candidate", reasons=reasons),
            ),
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


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(
            RotationAction(
                0.0,
                0,
                RotationActionKind.POTION,
                "Essence of Spell Power",
            ),
            RotationAction(
                30.0,
                0,
                RotationActionKind.POTION,
                "Essence of Health",
            ),
        ),
    )


def test_canonical_candidate_enforces_shared_potion_cadence_across_names() -> None:
    plan = _plan()
    pipeline = _Pipeline(plan)
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        potion_cadence_requirement=RotationPotionCadenceRequirement(45.0),
    )

    assert pipeline.scorecard is not None
    assert len(pipeline.scorecard.cooldown_violations) == 1
    violation = pipeline.scorecard.cooldown_violations[0]
    assert violation.requirement.action_kind is RotationActionKind.POTION
    assert violation.requirement.action_name == "Essence of Health"
    assert violation.actual_interval_seconds == 30.0
    assert violation.required_interval_seconds == 45.0
    assert not pipeline.scorecard.supplied_obligations_satisfied
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is False


def test_canonical_candidate_does_not_guess_potion_cooldown_without_requirement() -> None:
    plan = _plan()
    pipeline = _Pipeline(plan)
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert pipeline.scorecard.cooldown_violations == ()
    assert result.validation.selectable is True
