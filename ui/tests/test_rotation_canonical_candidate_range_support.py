from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_action_range import (
    RotationActionRangeRequirement,
    RotationTargetDistanceWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_saved_build_action_range_service import (
    RotationSavedBuildActionRangeEvidence,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=object(), unresolved=())


class _RangeService:
    def __init__(self, evidence: RotationSavedBuildActionRangeEvidence) -> None:
        self.evidence = evidence
        self.calls = []

    def resolve(self, player_build):
        self.calls.append(player_build)
        return self.evidence


class _Pipeline:
    def __init__(self, final_plan: RotationPlan) -> None:
        self.final_plan = final_plan
        self.scorecard = None

    def run_effects(self, **kwargs):
        snapshot = SimpleNamespace(candidate_id="range-candidate", plan=self.final_plan)
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(
                candidate_id="range-candidate",
                reasons=("all tracked hard obligations satisfied",),
            )
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        reasons = (
            ("all tracked hard obligations satisfied",)
            if selected is not None
            else ("canonical action range legality failed",)
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(
                SimpleNamespace(candidate_id="range-candidate", reasons=reasons),
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
                42.0,
                0,
                RotationActionKind.SKILL,
                "Ranged Heal",
                "front",
            ),
        ),
    )


def test_canonical_candidate_applies_saved_build_range_to_final_stabilized_scorecard() -> None:
    evidence = RotationSavedBuildActionRangeEvidence(
        range_requirements=(
            RotationActionRangeRequirement(
                action_name="Ranged Heal",
                maximum_range=28.0,
            ),
        ),
    )
    range_service = _RangeService(evidence)
    pipeline = _Pipeline(_plan())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_range_service=range_service,
    )
    player_build = object()

    result = support.run_effects(
        player_build=player_build,
        seed_plan=_plan(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        target_distance_windows=(
            RotationTargetDistanceWindow(
                name="Cage rescue",
                start_seconds=40.0,
                end_seconds=46.0,
                distance=32.0,
            ),
        ),
    )

    assert range_service.calls == [player_build]
    assert pipeline.scorecard is not None
    assert len(pipeline.scorecard.range_violations) == 1
    violation = pipeline.scorecard.range_violations[0]
    assert violation.window_name == "Cage rescue"
    assert violation.distance == 32.0
    assert violation.maximum_range == 28.0
    assert not pipeline.scorecard.supplied_obligations_satisfied
    assert result.action_range_evidence is evidence
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is False
    assert result.validation.selected_candidate_id is None


def test_saved_build_range_is_retained_without_guessing_distance_when_no_window_is_supplied() -> None:
    evidence = RotationSavedBuildActionRangeEvidence(
        range_requirements=(
            RotationActionRangeRequirement(
                action_name="Ranged Heal",
                maximum_range=28.0,
            ),
        ),
    )
    pipeline = _Pipeline(_plan())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_range_service=_RangeService(evidence),
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=_plan(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert result.action_range_evidence is evidence
    assert pipeline.scorecard.range_violations == ()
    assert result.validation.selectable is True
