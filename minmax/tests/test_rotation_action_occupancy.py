from __future__ import annotations

import pytest

from minmax.rotation_action_occupancy import (
    RotationActionOccupancyAssessor,
    RotationActionOccupancyRequirement,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_occupancy_violation_reports_blocked_skill_inside_window() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Channeled Skill", "front"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, "Followup Skill", "front"),
        RotationAction(13.0, 0, RotationActionKind.SKILL, "Late Skill", "front"),
    )
    requirement = RotationActionOccupancyRequirement("Channeled Skill", 2.0)

    result = RotationActionOccupancyAssessor().assess(plan, (requirement,))

    assert not result.legal
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.occupying_time_seconds == 10.0
    assert violation.occupying_until_seconds == 12.0
    assert violation.blocked_time_seconds == 11.0
    assert violation.blocked_action_name == "Followup Skill"


def test_exact_occupancy_boundary_is_legal_and_nonblocking_actions_are_ignored() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Cast Skill", "front"),
        RotationAction(10.5, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        RotationAction(10.7, 0, RotationActionKind.POTION, "Potion", None),
        RotationAction(12.0, 0, RotationActionKind.ULTIMATE, "Boundary Ultimate", "front"),
    )

    result = RotationActionOccupancyAssessor().assess(
        plan,
        (RotationActionOccupancyRequirement("Cast Skill", 2.0),),
    )

    assert result.legal


def test_bar_scope_and_invalid_requirements_fail_closed() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Shared Skill", "back"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, "Other Skill", "front"),
    )
    front_only = RotationActionOccupancyRequirement(
        "Shared Skill",
        2.0,
        bar="front",
    )
    assert RotationActionOccupancyAssessor().assess(plan, (front_only,)).legal

    with pytest.raises(ValueError, match="finite and non-negative"):
        RotationActionOccupancyRequirement("Skill", -1.0)

    with pytest.raises(ValueError, match="skill or ultimate"):
        RotationActionOccupancyRequirement(
            "Potion",
            1.0,
            action_kind=RotationActionKind.POTION,
        )

    duplicate = RotationActionOccupancyRequirement("Skill", 1.0)
    with pytest.raises(ValueError, match="duplicate rotation occupancy requirement"):
        RotationActionOccupancyAssessor().assess(plan, (duplicate, duplicate))
