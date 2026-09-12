from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateSharedEvaluationContext,
)
from services.rotation_generate_candidate_resolver_service import (
    RotationGenerateCandidateResolverService,
)


class _SustainService:
    def __init__(self) -> None:
        self.calls = []
        self.baseline = object()

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return self.baseline


class _DurationService:
    def __init__(self) -> None:
        self.calls = []

    def analyze(self, plan):
        self.calls.append(plan)
        return ("duration", plan)


class _ScorecardService:
    def __init__(self) -> None:
        self.calls = []

    def compare(self, **kwargs):
        self.calls.append(kwargs)
        return ("scorecard", kwargs["candidate_plan"])


class _RankingService:
    def __init__(self) -> None:
        self.calls = []

    def rank(self, candidates):
        self.calls.append(candidates)
        item = candidates[0]
        return (
            SimpleNamespace(
                candidate_id=item.candidate_id,
                scorecard=item.scorecard,
            ),
        )


def test_generate_resolvers_reuse_canonical_sustain_scorecard_and_ranking_services() -> None:
    sustain = _SustainService()
    duration = _DurationService()
    scorecards = _ScorecardService()
    ranking = _RankingService()
    service = RotationGenerateCandidateResolverService(
        sustain_service=sustain,  # type: ignore[arg-type]
        duration_service=duration,  # type: ignore[arg-type]
        scorecard_service=scorecards,  # type: ignore[arg-type]
        ranking_service=ranking,  # type: ignore[arg-type]
    )
    build = object()
    baseline_plan = object()
    demand = object()
    context = RotationCandidateSharedEvaluationContext(
        demands=(demand,),  # type: ignore[arg-type]
    )

    resolvers = service.build(
        player_build=build,  # type: ignore[arg-type]
        baseline_plan=baseline_plan,  # type: ignore[arg-type]
        resource=ResourceType.MAGICKA,
        context=context,
    )

    assert sustain.calls == [
        {
            "build": build,
            "plan": baseline_plan,
            "resource": ResourceType.MAGICKA,
        }
    ]
    assert resolvers.baseline_sustain is sustain.baseline

    candidate_plan = object()
    candidate_sustain = object()
    replay = SimpleNamespace(final_projection=candidate_sustain)
    ranked = resolvers.evaluator_resolver("candidate-a")(candidate_plan, replay)

    assert ranked.candidate_id == "candidate-a"
    assert len(ranking.calls) == 1
    assert ranking.calls[0][0].candidate_id == "candidate-a"
    assert scorecards.calls[0]["baseline_plan"] is baseline_plan
    assert scorecards.calls[0]["candidate_plan"] is candidate_plan
    assert scorecards.calls[0]["baseline_sustain"] is sustain.baseline
    assert scorecards.calls[0]["candidate_sustain"] is candidate_sustain
    assert scorecards.calls[0]["demands"] == (demand,)
    assert scorecards.calls[0]["candidate_duration"] == ("duration", candidate_plan)

    final_plan = object()
    final_sustain = object()
    final_scorecard = resolvers.scorecard_resolver(
        SimpleNamespace(
            plan=final_plan,
            replay=SimpleNamespace(final_projection=final_sustain),
        )
    )

    assert final_scorecard == ("scorecard", final_plan)
    assert scorecards.calls[1]["baseline_plan"] is baseline_plan
    assert scorecards.calls[1]["candidate_plan"] is final_plan
    assert scorecards.calls[1]["candidate_sustain"] is final_sustain
    assert duration.calls == [candidate_plan, final_plan]


def test_generate_candidate_evaluator_rejects_empty_candidate_id() -> None:
    service = RotationGenerateCandidateResolverService(
        sustain_service=_SustainService(),  # type: ignore[arg-type]
        duration_service=_DurationService(),  # type: ignore[arg-type]
        scorecard_service=_ScorecardService(),  # type: ignore[arg-type]
        ranking_service=_RankingService(),  # type: ignore[arg-type]
    )

    resolvers = service.build(
        player_build=object(),  # type: ignore[arg-type]
        baseline_plan=object(),  # type: ignore[arg-type]
        resource=ResourceType.MAGICKA,
    )

    try:
        resolvers.evaluator_resolver("   ")
    except ValueError as exc:
        assert str(exc) == "rotation Generate candidate evaluator requires candidate_id"
    else:
        raise AssertionError("empty candidate_id should be rejected")
