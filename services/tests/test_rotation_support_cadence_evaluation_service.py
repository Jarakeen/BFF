from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_support_cadence_candidate_service import (
    RotationSupportCadencePlanCandidate,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
    RotationSupportCadenceEvaluationService,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name=name,
                bar="front",
            ),
        ),
    )


def _candidate(candidate_id: str, *, plan_name: str, rationale: str = "because math"):
    plan = _plan(plan_name)
    cadence = SimpleNamespace(rationale=rationale)
    refinement = SimpleNamespace(
        plan=plan,
        duration_projection=SimpleNamespace(marker=f"duration:{candidate_id}"),
    )
    return RotationSupportCadencePlanCandidate(
        candidate_id=candidate_id,
        effect_key="major_slayer",
        source_skill_id="combat_prayer",
        cadence=cadence,
        refresh_policy=SimpleNamespace(),
        refinement=refinement,
    )


class _SustainService:
    def __init__(self) -> None:
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            marker=f"sustain:{kwargs['plan'].actions[0].name}",
            resource=kwargs["resource"],
            unresolved=(),
        )


class _ScorecardService:
    def __init__(self) -> None:
        self.calls = []

    def compare(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(marker=f"score:{kwargs['candidate_plan'].actions[0].name}")


class _EffectRanker:
    def __init__(self) -> None:
        self.calls = []

    def rank(self, candidates):
        self.calls.append(candidates)
        return tuple(
            SimpleNamespace(
                candidate_id=item.ranking_input.candidate_id,
                assessments=item.effect_uptime_assessments,
            )
            for item in candidates
        )


def test_evaluates_each_complete_candidate_through_sustain_and_scorecard() -> None:
    sustain = _SustainService()
    scorecards = _ScorecardService()
    service = RotationSupportCadenceEvaluationService(
        sustain_service=sustain,
        scorecard_service=scorecards,
        effect_obligation_ranker=_EffectRanker(),
    )
    baseline_plan = _plan("Baseline Skill")
    baseline_sustain = SimpleNamespace(marker="baseline sustain")
    candidates = (
        _candidate("major_slayer:combat_prayer:full_coverage", plan_name="Full Plan"),
        _candidate("major_slayer:combat_prayer:target_floor", plan_name="Floor Plan"),
    )

    result = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=baseline_plan,
        baseline_sustain=baseline_sustain,
        candidates=candidates,
    )

    assert [item.candidate_id for item in result] == [
        "major_slayer:combat_prayer:full_coverage",
        "major_slayer:combat_prayer:target_floor",
    ]
    assert [call["plan"] for call in sustain.calls] == [
        candidates[0].plan,
        candidates[1].plan,
    ]
    assert all(call["resource"] is ResourceType.MAGICKA for call in sustain.calls)
    assert [call["candidate_duration"] for call in scorecards.calls] == [
        candidates[0].refinement.duration_projection,
        candidates[1].refinement.duration_projection,
    ]
    assert all(call["baseline_plan"] is baseline_plan for call in scorecards.calls)
    assert all(call["baseline_sustain"] is baseline_sustain for call in scorecards.calls)
    assert [item.ranking_input.scorecard for item in result] == [
        result[0].scorecard,
        result[1].scorecard,
    ]


def test_forwards_explicit_evaluation_context_without_inventing_policy() -> None:
    sustain = _SustainService()
    scorecards = _ScorecardService()
    service = RotationSupportCadenceEvaluationService(
        sustain_service=sustain,
        scorecard_service=scorecards,
        effect_obligation_ranker=_EffectRanker(),
    )
    candidate = _candidate("candidate", plan_name="Candidate Plan")
    demand = SimpleNamespace(name="burn")
    uptime_requirement = SimpleNamespace(skill_name="Combat Prayer")
    restoration = SimpleNamespace(source="orb")
    context = RotationSupportCadenceEvaluationContext(
        resource=ResourceType.STAMINA,
        restoration_events=(restoration,),
        demands=(demand,),
        runtime_uptime_requirements=(uptime_requirement,),
    )

    service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=_plan("Baseline Skill"),
        baseline_sustain=SimpleNamespace(),
        candidates=(candidate,),
        context=context,
    )

    assert sustain.calls[0]["resource"] is ResourceType.STAMINA
    assert sustain.calls[0]["restoration_events"] == (restoration,)
    assert scorecards.calls[0]["demands"] == (demand,)
    assert scorecards.calls[0]["runtime_uptime_requirements"] == (uptime_requirement,)


def test_preserves_candidate_cadence_rationale_for_explanations() -> None:
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
        effect_obligation_ranker=_EffectRanker(),
    )
    candidate = _candidate(
        "candidate",
        plan_name="Candidate Plan",
        rationale="longest cadence meeting the explicit uptime floor",
    )

    result = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=_plan("Baseline Skill"),
        baseline_sustain=SimpleNamespace(),
        candidates=(candidate,),
    )

    assert result[0].rationale == "longest cadence meeting the explicit uptime floor"


def test_duplicate_candidate_ids_are_rejected_before_evaluation() -> None:
    sustain = _SustainService()
    service = RotationSupportCadenceEvaluationService(
        sustain_service=sustain,
        scorecard_service=_ScorecardService(),
        effect_obligation_ranker=_EffectRanker(),
    )

    with pytest.raises(ValueError, match="duplicate support cadence candidate_id"):
        service.evaluate(
            build=SimpleNamespace(),
            baseline_plan=_plan("Baseline Skill"),
            baseline_sustain=SimpleNamespace(),
            candidates=(
                _candidate("same", plan_name="One"),
                _candidate("SAME", plan_name="Two"),
            ),
        )

    assert sustain.calls == []


def test_rank_wraps_existing_ranking_inputs_with_exact_effect_assessments() -> None:
    ranker = _EffectRanker()
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
        effect_obligation_ranker=ranker,
    )
    candidates = (
        _candidate("full", plan_name="Full"),
        _candidate("floor", plan_name="Floor"),
    )
    evaluated = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=_plan("Baseline Skill"),
        baseline_sustain=SimpleNamespace(),
        candidates=candidates,
    )
    full_assessment = SimpleNamespace(requirement=SimpleNamespace(effect_name="Major Slayer"))
    floor_assessment = SimpleNamespace(requirement=SimpleNamespace(effect_name="Major Slayer"))

    ranked = service.rank(
        evaluated,
        effect_uptime_assessments_by_candidate={
            "FULL": (full_assessment,),
            "floor": (floor_assessment,),
        },
    )

    assert [item.candidate_id for item in ranked] == ["full", "floor"]
    assert ranked[0].assessments == (full_assessment,)
    assert ranked[1].assessments == (floor_assessment,)
    assert ranker.calls[0][0].ranking_input is evaluated[0].ranking_input
    assert ranker.calls[0][1].ranking_input is evaluated[1].ranking_input


def test_rank_without_effect_assessments_uses_existing_base_ranking_path() -> None:
    ranker = _EffectRanker()
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
        effect_obligation_ranker=ranker,
    )
    evaluated = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=_plan("Baseline Skill"),
        baseline_sustain=SimpleNamespace(),
        candidates=(_candidate("candidate", plan_name="Candidate"),),
    )

    ranked = service.rank(evaluated)

    assert ranked[0].candidate_id == "candidate"
    assert ranked[0].assessments == ()


def test_effect_assessment_map_must_match_evaluated_candidate_set_exactly() -> None:
    service = RotationSupportCadenceEvaluationService(
        sustain_service=_SustainService(),
        scorecard_service=_ScorecardService(),
        effect_obligation_ranker=_EffectRanker(),
    )
    evaluated = service.evaluate(
        build=SimpleNamespace(),
        baseline_plan=_plan("Baseline Skill"),
        baseline_sustain=SimpleNamespace(),
        candidates=(
            _candidate("full", plan_name="Full"),
            _candidate("floor", plan_name="Floor"),
        ),
    )

    with pytest.raises(ValueError, match="must exactly match evaluated candidates"):
        service.rank(
            evaluated,
            effect_uptime_assessments_by_candidate={"full": ()},
        )
