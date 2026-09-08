from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService


def _plan(*, unresolved=()) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        actions=(),
        unresolved=tuple(unresolved),
    )


def _sustain(*, unresolved=()):
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30_000,
        ending_amount=30_000,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(timeline=timeline, action_cost_events=()),
        unresolved=tuple(unresolved),
    )


def test_inherited_unresolved_remains_diagnostic_but_candidate_specific_is_hard() -> None:
    service = RotationCandidateScorecardService()
    baseline = _plan(unresolved=("shared limitation",))

    inherited = service.compare(
        baseline_plan=baseline,
        candidate_plan=_plan(unresolved=("shared limitation",)),
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
    )
    candidate_specific = service.compare(
        baseline_plan=baseline,
        candidate_plan=_plan(unresolved=("shared limitation", "candidate-only gap")),
        baseline_sustain=_sustain(),
        candidate_sustain=_sustain(),
    )

    assert inherited.inherited_unresolved == ("shared limitation",)
    assert inherited.candidate_specific_unresolved == ()
    assert inherited.supplied_obligations_satisfied

    assert candidate_specific.inherited_unresolved == ("shared limitation",)
    assert candidate_specific.candidate_specific_unresolved == ("candidate-only gap",)
    assert not candidate_specific.supplied_obligations_satisfied
