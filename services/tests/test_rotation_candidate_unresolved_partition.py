from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecardService


def _plan(*, unresolved=()) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
        unresolved=tuple(unresolved),
    )


def _sustain(*, unresolved=()):
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=30000,
        events=(),
    )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            timeline=timeline,
            action_cost_events=(),
        ),
        unresolved=tuple(unresolved),
    )


def test_shared_baseline_unresolved_is_inherited_and_candidate_addition_is_specific() -> None:
    shared = "rotation sustain currently infers equipped armor skill-line ownership"
    candidate_only = "candidate-specific unresolved duration interaction"

    result = RotationCandidateScorecardService().compare(
        baseline_plan=_plan(unresolved=(shared,)),
        candidate_plan=_plan(unresolved=(shared, candidate_only)),
        baseline_sustain=_sustain(unresolved=(shared,)),
        candidate_sustain=_sustain(unresolved=(shared, candidate_only)),
    )

    assert result.inherited_unresolved == (shared,)
    assert result.candidate_specific_unresolved == (candidate_only,)
    assert result.unresolved == (shared, candidate_only)


def test_baseline_only_unresolved_does_not_appear_as_candidate_evidence() -> None:
    baseline_only = "baseline-only diagnostic"

    result = RotationCandidateScorecardService().compare(
        baseline_plan=_plan(unresolved=(baseline_only,)),
        candidate_plan=_plan(),
        baseline_sustain=_sustain(unresolved=(baseline_only,)),
        candidate_sustain=_sustain(),
    )

    assert result.inherited_unresolved == ()
    assert result.candidate_specific_unresolved == ()
    assert result.unresolved == ()
