from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
    RotationSupportCadenceEvaluationService,
)


class _SustainService:
    def evaluate(self, **_kwargs):
        return SimpleNamespace(unresolved=())


class _ScorecardService:
    def compare(self, **_kwargs):
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


def _candidate(candidate_id: str) -> SimpleNamespace:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=10.0,
        actions=(),
    )
    return SimpleNamespace(
        candidate_id=candidate_id,
        plan=plan,
        refinement=SimpleNamespace(duration_projection=None),
    )


def test_candidate_hard_obligation_resolver_marks_only_failing_candidate() -> None:
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
    )
    candidates = (_candidate("good"), _candidate("bad"))

    def resolve(plan: RotationPlan) -> tuple[str, ...]:
        # Candidate plans are deliberately distinguishable only by identity supplied
        # through closure order here; the important contract is that the resolver is
        # invoked independently for each completed plan before ranking.
        resolve.calls += 1
        return () if resolve.calls == 1 else ("Aggressive Horn not ready at landing 2",)

    resolve.calls = 0
    evaluated = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=candidates[0].plan,
        baseline_sustain=SimpleNamespace(),
        candidates=candidates,
        context=RotationSupportCadenceEvaluationContext(
            candidate_hard_obligation_resolver=resolve,
        ),
    )

    assert evaluated[0].scorecard.supplied_obligations_satisfied is True
    assert evaluated[0].scorecard.candidate_specific_unresolved == ()
    assert evaluated[1].scorecard.supplied_obligations_satisfied is False
    assert evaluated[1].scorecard.candidate_specific_unresolved == (
        "Aggressive Horn not ready at landing 2",
    )
    assert evaluated[1].ranking_input.scorecard is evaluated[1].scorecard


def test_candidate_hard_obligation_evidence_is_deduplicated() -> None:
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
    )
    candidate = _candidate("one")

    evaluated = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=candidate.plan,
        baseline_sustain=SimpleNamespace(),
        candidates=(candidate,),
        context=RotationSupportCadenceEvaluationContext(
            candidate_hard_obligation_resolver=lambda _plan: (
                "Horn shortfall",
                "horn shortfall",
                "",
            ),
        ),
    )

    assert evaluated[0].scorecard.candidate_specific_unresolved == ("Horn shortfall",)
