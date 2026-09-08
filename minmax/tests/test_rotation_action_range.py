from __future__ import annotations

import pytest

from minmax.rotation_action_range import (
    RotationActionRangeAssessor,
    RotationActionRangeRequirement,
    RotationTargetDistanceWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_range_assessment_reports_too_close_and_too_far_actions() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Ranged Skill", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Ranged Skill", "front"),
    )
    requirement = RotationActionRangeRequirement(
        "Ranged Skill",
        minimum_range=5.0,
        maximum_range=28.0,
    )
    windows = (
        RotationTargetDistanceWindow("Too close", 9.0, 11.0, 3.0),
        RotationTargetDistanceWindow("Too far", 19.0, 21.0, 32.0),
    )

    result = RotationActionRangeAssessor().assess(plan, (requirement,), windows)

    assert not result.legal
    assert len(result.violations) == 2
    assert result.violations[0].window_name == "Too close"
    assert result.violations[0].reason == "target is inside the action's minimum range"
    assert result.violations[1].window_name == "Too far"
    assert result.violations[1].reason == "target is outside the action's maximum range"


def test_exact_range_boundaries_are_legal_and_bar_scope_is_optional() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Shared Skill", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Shared Skill", "back"),
        RotationAction(30.0, 0, RotationActionKind.SKILL, "Shared Skill", "front"),
    )
    windows = (
        RotationTargetDistanceWindow("Minimum boundary", 9.0, 11.0, 5.0),
        RotationTargetDistanceWindow("Back too far", 19.0, 21.0, 40.0),
        RotationTargetDistanceWindow("Maximum boundary", 29.0, 31.0, 28.0),
    )

    global_result = RotationActionRangeAssessor().assess(
        plan,
        (RotationActionRangeRequirement("Shared Skill", 5.0, 28.0),),
        windows,
    )
    front_only_result = RotationActionRangeAssessor().assess(
        plan,
        (RotationActionRangeRequirement("Shared Skill", 5.0, 28.0, bar="front"),),
        windows,
    )

    assert not global_result.legal
    assert len(global_result.violations) == 1
    assert global_result.violations[0].time_seconds == 20.0
    assert front_only_result.legal


def test_range_assessment_only_evaluates_explicit_distance_windows() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Ranged Skill", "front"),
        RotationAction(50.0, 0, RotationActionKind.SKILL, "Ranged Skill", "front"),
    )
    requirement = RotationActionRangeRequirement("Ranged Skill", maximum_range=28.0)
    windows = (RotationTargetDistanceWindow("Known distance", 9.0, 11.0, 20.0),)

    result = RotationActionRangeAssessor().assess(plan, (requirement,), windows)

    assert result.legal


def test_invalid_range_evidence_and_overlapping_windows_fail_closed() -> None:
    with pytest.raises(ValueError, match="minimum range"):
        RotationActionRangeRequirement("Skill", minimum_range=-1.0, maximum_range=28.0)

    with pytest.raises(ValueError, match="maximum range"):
        RotationActionRangeRequirement("Skill", minimum_range=10.0, maximum_range=5.0)

    with pytest.raises(ValueError, match="skill or ultimate"):
        RotationActionRangeRequirement(
            "Potion",
            maximum_range=28.0,
            action_kind=RotationActionKind.POTION,
        )

    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Skill", "front"),
    )
    duplicate = RotationActionRangeRequirement("Skill", maximum_range=28.0)
    with pytest.raises(ValueError, match="duplicate rotation range requirement"):
        RotationActionRangeAssessor().assess(
            plan,
            (duplicate, duplicate),
            (RotationTargetDistanceWindow("Known", 9.0, 11.0, 20.0),),
        )

    with pytest.raises(ValueError, match="cannot overlap"):
        RotationActionRangeAssessor().assess(
            plan,
            (duplicate,),
            (
                RotationTargetDistanceWindow("First", 9.0, 12.0, 20.0),
                RotationTargetDistanceWindow("Second", 11.0, 13.0, 20.0),
            ),
        )
