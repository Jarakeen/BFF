from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhood,
)
from services.rotation_support_cadence_progression_service import (
    RotationSupportCadenceProgressionService,
)


def _plan(name: str) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name=name,
        duration_seconds=30.0,
        actions=(),
    )


class _NeighborhoodService:
    def __init__(self, neighborhood):
        self.neighborhood = neighborhood
        self.calls = []

    def generate(self, *, seed_plan, obligations, priorities=None):
        self.calls.append(
            {
                "seed_plan": seed_plan,
                "obligations": obligations,
                "priorities": priorities,
            }
        )
        return self.neighborhood


class _EvaluationService:
    def __init__(self, evaluated=(), ranking=()):
        self.evaluated = tuple(evaluated)
        self.ranking = tuple(ranking)
        self.evaluate_calls = []
        self.rank_calls = []

    def evaluate(
        self,
        *,
        build,
        baseline_plan,
        baseline_sustain,
        candidates,
        context=None,
    ):
        self.evaluate_calls.append(
            {
                "build": build,
                "baseline_plan": baseline_plan,
                "baseline_sustain": baseline_sustain,
                "candidates": tuple(candidates),
                "context": context,
            }
        )
        return self.evaluated

    def rank(self, evaluated, *, effect_uptime_assessments_by_candidate=None):
        self.rank_calls.append(
            {
                "evaluated": tuple(evaluated),
                "effect_uptime_assessments_by_candidate": effect_uptime_assessments_by_candidate,
            }
        )
        return self.ranking


class _RecommendationService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def recommend(self, *, evaluated, ranking):
        self.calls.append(
            {
                "evaluated": tuple(evaluated),
                "ranking": tuple(ranking),
            }
        )
        return self.result


def _service(*, seed, candidates, evaluated, ranking, recommendation, unresolved=()):
    neighborhood = RotationSupportCadenceNeighborhood(
        seed_plan=seed,
        candidates=tuple(candidates),
        unresolved=tuple(unresolved),
    )
    neighborhood_service = _NeighborhoodService(neighborhood)
    evaluation_service = _EvaluationService(evaluated=evaluated, ranking=ranking)
    recommendation_service = _RecommendationService(recommendation)
    service = RotationSupportCadenceProgressionService(
        neighborhood_service=neighborhood_service,
        evaluation_service=evaluation_service,
        recommendation_service=recommendation_service,
    )
    return service, neighborhood_service, evaluation_service, recommendation_service


def test_promotes_recommended_complete_plan_and_its_sustain_as_next_seed() -> None:
    seed = _plan("Seed")
    promoted_plan = _plan("Promoted")
    seed_sustain = object()
    promoted_sustain = object()
    raw_candidate = object()
    evaluated = SimpleNamespace(
        candidate_id="minor_berserk:combat_prayer:target_floor",
        candidate=SimpleNamespace(plan=promoted_plan),
        sustain=promoted_sustain,
    )
    ranking = object()
    recommended = SimpleNamespace(evaluated=evaluated)
    recommendation = SimpleNamespace(recommended=recommended)
    service, _, evaluation_service, _ = _service(
        seed=seed,
        candidates=(raw_candidate,),
        evaluated=(evaluated,),
        ranking=(ranking,),
        recommendation=recommendation,
    )

    result = service.step(
        build=object(),  # type: ignore[arg-type]
        seed_plan=seed,
        seed_sustain=seed_sustain,  # type: ignore[arg-type]
        obligations=(),
    )

    assert evaluation_service.evaluate_calls[0]["baseline_plan"] is seed
    assert evaluation_service.evaluate_calls[0]["baseline_sustain"] is seed_sustain
    assert result.next_seed_plan is promoted_plan
    assert result.next_seed_sustain is promoted_sustain
    assert result.promoted_candidate_id == "minor_berserk:combat_prayer:target_floor"
    assert result.advanced is True


def test_no_eligible_recommendation_retains_current_seed_and_sustain() -> None:
    seed = _plan("Seed")
    seed_sustain = object()
    evaluated = SimpleNamespace(candidate_id="candidate-a")
    recommendation = SimpleNamespace(recommended=None)
    service, _, _, _ = _service(
        seed=seed,
        candidates=(object(),),
        evaluated=(evaluated,),
        ranking=(object(),),
        recommendation=recommendation,
    )

    result = service.step(
        build=object(),  # type: ignore[arg-type]
        seed_plan=seed,
        seed_sustain=seed_sustain,  # type: ignore[arg-type]
        obligations=(),
    )

    assert result.next_seed_plan is seed
    assert result.next_seed_sustain is seed_sustain
    assert result.promoted_candidate_id is None
    assert result.advanced is False


def test_step_forwards_neighborhood_evaluation_and_effect_evidence_without_inference() -> None:
    seed = _plan("Seed")
    raw_candidate = object()
    evaluated = SimpleNamespace(candidate_id="candidate-a")
    ranking = object()
    recommendation = SimpleNamespace(recommended=None)
    service, neighborhood_service, evaluation_service, recommendation_service = _service(
        seed=seed,
        candidates=(raw_candidate,),
        evaluated=(evaluated,),
        ranking=(ranking,),
        recommendation=recommendation,
    )
    build = object()
    seed_sustain = object()
    priorities = object()
    context = object()
    obligations = (object(), object())
    effect_map = {"candidate-a": (object(),)}

    result = service.step(
        build=build,  # type: ignore[arg-type]
        seed_plan=seed,
        seed_sustain=seed_sustain,  # type: ignore[arg-type]
        obligations=obligations,  # type: ignore[arg-type]
        priorities=priorities,  # type: ignore[arg-type]
        evaluation_context=context,  # type: ignore[arg-type]
        effect_uptime_assessments_by_candidate=effect_map,  # type: ignore[arg-type]
    )

    assert neighborhood_service.calls == [
        {"seed_plan": seed, "obligations": obligations, "priorities": priorities}
    ]
    assert evaluation_service.evaluate_calls[0]["build"] is build
    assert evaluation_service.evaluate_calls[0]["candidates"] == (raw_candidate,)
    assert evaluation_service.evaluate_calls[0]["context"] is context
    assert evaluation_service.rank_calls == [
        {
            "evaluated": (evaluated,),
            "effect_uptime_assessments_by_candidate": effect_map,
        }
    ]
    assert recommendation_service.calls == [
        {"evaluated": (evaluated,), "ranking": (ranking,)}
    ]
    assert result.evaluated == (evaluated,)
    assert result.ranking == (ranking,)


def test_neighborhood_unresolved_evidence_is_preserved_on_step_result() -> None:
    seed = _plan("Seed")
    recommendation = SimpleNamespace(recommended=None)
    service, _, _, _ = _service(
        seed=seed,
        candidates=(),
        evaluated=(),
        ranking=(),
        recommendation=recommendation,
        unresolved=("major_courage: duration unresolved",),
    )

    result = service.step(
        build=object(),  # type: ignore[arg-type]
        seed_plan=seed,
        seed_sustain=object(),  # type: ignore[arg-type]
        obligations=(),
    )

    assert result.unresolved == ("major_courage: duration unresolved",)
    assert result.advanced is False


def test_empty_neighborhood_still_composes_empty_evaluation_ranking_and_recommendation() -> None:
    seed = _plan("Seed")
    seed_sustain = object()
    recommendation = SimpleNamespace(recommended=None)
    service, _, evaluation_service, recommendation_service = _service(
        seed=seed,
        candidates=(),
        evaluated=(),
        ranking=(),
        recommendation=recommendation,
    )

    result = service.step(
        build=object(),  # type: ignore[arg-type]
        seed_plan=seed,
        seed_sustain=seed_sustain,  # type: ignore[arg-type]
        obligations=(),
    )

    assert evaluation_service.evaluate_calls[0]["candidates"] == ()
    assert evaluation_service.rank_calls[0]["evaluated"] == ()
    assert recommendation_service.calls == [{"evaluated": (), "ranking": ()}]
    assert result.next_seed_plan is seed
    assert result.next_seed_sustain is seed_sustain
