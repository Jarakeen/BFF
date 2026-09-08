from types import SimpleNamespace

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from ui.rotation_weapon_attack_candidate_support import (
    RotationWeaponAttackCandidateSupport,
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
        candidate_specific_unresolved=("existing candidate gap",),
    )


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=(),
    )


class _Adapter:
    def __init__(self, adaptation) -> None:
        self.adaptation = adaptation
        self.calls = []

    def adapt(self, player_build, *, character_id=None):
        self.calls.append((player_build, character_id))
        return self.adaptation


class _Projection:
    def __init__(self, unresolved=()) -> None:
        self.unresolved = tuple(unresolved)
        self.calls = []

    def project(self, *, build, plan, initial_bar):
        self.calls.append((build, plan, initial_bar))
        return SimpleNamespace(unresolved=self.unresolved, violations=(), resolutions=())


class _Delegate:
    def __init__(self) -> None:
        self.calls = []
        self.scorecard = None

    def run_effects(self, **kwargs):
        self.calls.append(kwargs)
        snapshot = SimpleNamespace(candidate_id="candidate", plan=_plan())
        self.scorecard = kwargs["scorecard_resolver"](snapshot)
        return SimpleNamespace(scorecard=self.scorecard)


def test_wrapper_promotes_final_plan_weapon_identity_gap_to_candidate_unresolved() -> None:
    canonical_build = object()
    adapter = _Adapter(SimpleNamespace(build=canonical_build, unresolved=()))
    projection = _Projection(("scheduled light attack uses an unavailable back bar",))
    delegate = _Delegate()
    support = RotationWeaponAttackCandidateSupport(
        canonical_candidates=delegate,
        build_adapter=adapter,
        projection_service=projection,
    )
    player_build = object()

    support.run_effects(
        player_build=player_build,
        character_id="magrat-id",
        initial_bar="front",
        scorecard_resolver=_scorecard,
    )

    assert adapter.calls == [(player_build, "magrat-id")]
    assert projection.calls == [(canonical_build, _plan(), "front")]
    assert delegate.scorecard is not None
    assert delegate.scorecard.candidate_specific_unresolved == (
        "existing candidate gap",
        "scheduled light attack uses an unavailable back bar",
    )
    assert delegate.scorecard.supplied_obligations_satisfied is False


def test_wrapper_preserves_core_not_evaluated_path_when_build_adaptation_is_unresolved() -> None:
    adapter = _Adapter(SimpleNamespace(build=object(), unresolved=("weapon unresolved",)))
    projection = _Projection(("should not run",))
    delegate = _Delegate()
    support = RotationWeaponAttackCandidateSupport(
        canonical_candidates=delegate,
        build_adapter=adapter,
        projection_service=projection,
    )

    support.run_effects(
        player_build=object(),
        scorecard_resolver=_scorecard,
    )

    assert projection.calls == []
    assert delegate.scorecard is not None
    assert delegate.scorecard.candidate_specific_unresolved == (
        "existing candidate gap",
    )
