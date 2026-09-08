from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.saved_build_adapter import SavedBuildAdaptation
from minmax.resource_costs import ResourceType
from minmax.rotation_action_cooldown import RotationActionCooldownRequirement
from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_saved_build_action_timing_service import (
    RotationSavedBuildActionTimingEvidence,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_recovery_validation_support import RotationRecoveryValidationScope


class _Adapter:
    def adapt(self, saved, *, character_id=None):
        return SavedBuildAdaptation(build=object(), unresolved=())


class _TimingService:
    def __init__(self, evidence: RotationSavedBuildActionTimingEvidence) -> None:
        self.evidence = evidence
        self.calls = []

    def resolve(self, player_build):
        self.calls.append(player_build)
        return self.evidence


class _Pipeline:
    def __init__(self, final_plan: RotationPlan) -> None:
        self.final_plan = final_plan
        self.scorecard = None
        self.calls = []

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        snapshot = SimpleNamespace(
            candidate_id="timing-candidate",
            plan=self.final_plan,
        )
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        selected = (
            SimpleNamespace(
                candidate_id="timing-candidate",
                reasons=("all tracked hard obligations satisfied",),
            )
            if self.scorecard.supplied_obligations_satisfied
            else None
        )
        reasons = (
            ("all tracked hard obligations satisfied",)
            if selected is not None
            else ("canonical action timing legality failed",)
        )
        return SimpleNamespace(
            selected_candidate=selected,
            ranked_candidates=(
                SimpleNamespace(
                    candidate_id="timing-candidate",
                    reasons=reasons,
                ),
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


def _final_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
            RotationAction(14.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
            RotationAction(20.0, 0, RotationActionKind.SKILL, "Channeled Skill", "front"),
            RotationAction(21.0, 0, RotationActionKind.SKILL, "Followup Skill", "front"),
        ),
    )


def test_canonical_candidate_applies_saved_build_timing_to_final_stabilized_scorecard() -> None:
    evidence = RotationSavedBuildActionTimingEvidence(
        cooldown_requirements=(
            RotationActionCooldownRequirement("Role Neutral Proc", 5.0),
        ),
        occupancy_requirements=(
            RotationActionOccupancyRequirement("Channeled Skill", 2.0),
        ),
    )
    timing_service = _TimingService(evidence)
    pipeline = _Pipeline(_final_plan())
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=timing_service,
    )
    player_build = object()

    result = support.run_effects(
        player_build=player_build,
        seed_plan=_final_plan(),
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert timing_service.calls == [player_build]
    assert pipeline.scorecard is not None
    assert len(pipeline.scorecard.cooldown_violations) == 1
    assert len(pipeline.scorecard.occupancy_violations) == 1
    assert not pipeline.scorecard.supplied_obligations_satisfied
    assert result.action_timing_evidence is evidence
    assert result.validation.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert result.validation.selectable is False
    assert result.validation.selected_candidate_id is None


def test_unresolved_saved_build_timing_is_retained_as_evidence_without_inventing_requirements() -> None:
    evidence = RotationSavedBuildActionTimingEvidence(
        unresolved=("canonical skill timing not found by exact saved name: Mystery Skill",),
    )
    timing_service = _TimingService(evidence)
    pipeline = _Pipeline(
        RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=10.0,
            actions=(),
        )
    )
    support = RotationCanonicalCandidateSupport(
        build_adapter=_Adapter(),
        pipeline=pipeline,
        action_timing_service=timing_service,
    )

    result = support.run_effects(
        player_build=object(),
        seed_plan=pipeline.final_plan,
        priorities=object(),
        evaluator_resolver=object(),
        scorecard_resolver=_scorecard,
        resource=ResourceType.MAGICKA,
        maximum_amount=30_000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
    )

    assert result.action_timing_evidence.unresolved == evidence.unresolved
    assert pipeline.scorecard.cooldown_violations == ()
    assert pipeline.scorecard.occupancy_violations == ()
    assert result.validation.selectable is True
