from __future__ import annotations

from minmax.local_refresh_cadence_duration_scheduler import (
    LocalRefreshCadenceDurationRotationScheduler,
)
from minmax.refresh_cadence_duration_scheduler import RotationRefreshIntervalPolicy
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


def _skill(time_seconds: float, name: str) -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name=name,
        bar="front",
    )


def _seed() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=40.0,
        actions=(
            _skill(0.0, "Effect A"),
            _skill(1.0, "Effect B"),
            _skill(5.0, "Filler"),
            _skill(10.0, "Filler"),
            _skill(11.0, "Effect B"),
            _skill(15.0, "Effect A"),
            _skill(20.0, "Filler"),
            _skill(21.0, "Effect B"),
            _skill(25.0, "Filler"),
            _skill(30.0, "Effect A"),
            _skill(31.0, "Effect B"),
            _skill(35.0, "Filler"),
        ),
    )


def _rules() -> tuple[RotationRecastRule, ...]:
    return (
        RotationRecastRule(
            skill_name="Effect A",
            duration_seconds=10.0,
            bar="front",
        ),
        RotationRecastRule(
            skill_name="Effect B",
            duration_seconds=10.0,
            bar="front",
        ),
    )


def _times(plan: RotationPlan, name: str) -> list[float]:
    return [
        action.time_seconds
        for action in plan.actions
        if action.kind is RotationActionKind.SKILL and action.name == name
    ]


def test_local_cadence_preserves_unrelated_accepted_duration_schedule() -> None:
    policy = RotationRefreshIntervalPolicy(
        skill_name="Effect B",
        interval_seconds=20.0,
        bar="front",
        source="test",
    )
    scheduler = LocalRefreshCadenceDurationRotationScheduler(
        (policy,),
        protected_duration_keys=(("effect a", "front"), ("effect b", "front")),
    )

    refined = scheduler.refine(_seed(), _rules())

    # Effect A is already an accepted 15-second cadence in the seed. Its canonical
    # duration is only 10 seconds, so the ordinary global duration scheduler would
    # pull it back toward 10-second refreshes. Local cadence refinement must not.
    assert _times(refined, "Effect A") == [0.0, 15.0, 30.0]
    assert _times(refined, "Effect B") == [1.0, 21.0]

    # Effect A is still a verified duration skill, so it may not be selected as a
    # filler when premature Effect B casts are removed.
    filler_times = _times(refined, "Filler")
    assert 11.0 in filler_times
    assert 31.0 in filler_times


def test_local_cadence_exposes_real_collision_instead_of_silently_preserving() -> None:
    policy = RotationRefreshIntervalPolicy(
        skill_name="Effect B",
        interval_seconds=14.0,
        bar="front",
        source="test",
    )
    scheduler = LocalRefreshCadenceDurationRotationScheduler(
        (policy,),
        protected_duration_keys=(("effect a", "front"), ("effect b", "front")),
    )

    refined = scheduler.refine(_seed(), _rules())

    # B becomes due exactly on A's accepted 15-second slot. That is genuine local
    # interference, so A is displaced rather than magically frozen. Downstream fresh
    # effect evidence can then reject this candidate if A's obligation regresses.
    assert _times(refined, "Effect B")[:2] == [1.0, 15.0]
    assert _times(refined, "Effect A")[:2] == [0.0, 20.0]
    assert any("displaced skill will cascade" in item for item in refined.unresolved)
