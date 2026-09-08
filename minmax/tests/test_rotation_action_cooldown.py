from __future__ import annotations

import pytest

from minmax.rotation_action_cooldown import (
    RotationActionCooldownAssessor,
    RotationActionCooldownRequirement,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_cooldown_violation_reports_actual_and_required_interval() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
        RotationAction(14.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Role Neutral Proc", "front"),
    )
    requirement = RotationActionCooldownRequirement(
        action_name="Role Neutral Proc",
        cooldown_seconds=5.0,
    )

    result = RotationActionCooldownAssessor().assess(plan, (requirement,))

    assert not result.legal
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.previous_time_seconds == 10.0
    assert violation.time_seconds == 14.0
    assert violation.actual_interval_seconds == 4.0
    assert violation.required_interval_seconds == 5.0


def test_exact_cooldown_boundary_is_legal_and_bar_scope_is_optional() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Shared Skill", "front"),
        RotationAction(12.0, 0, RotationActionKind.SKILL, "Shared Skill", "back"),
        RotationAction(15.0, 0, RotationActionKind.SKILL, "Shared Skill", "front"),
    )

    global_result = RotationActionCooldownAssessor().assess(
        plan,
        (RotationActionCooldownRequirement("Shared Skill", 5.0),),
    )
    front_only_result = RotationActionCooldownAssessor().assess(
        plan,
        (RotationActionCooldownRequirement("Shared Skill", 5.0, bar="front"),),
    )

    assert not global_result.legal
    assert len(global_result.violations) == 1
    assert global_result.violations[0].time_seconds == 12.0
    assert front_only_result.legal


def test_invalid_and_duplicate_cooldown_requirements_fail_closed() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        RotationActionCooldownRequirement("Skill", -1.0)

    with pytest.raises(ValueError, match="support skill, ultimate, or potion"):
        RotationActionCooldownRequirement(
            "Heavy",
            5.0,
            action_kind=RotationActionKind.HEAVY_ATTACK,
        )

    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Skill", "front"),
    )
    duplicate = RotationActionCooldownRequirement("Skill", 5.0)
    with pytest.raises(ValueError, match="duplicate rotation cooldown requirement"):
        RotationActionCooldownAssessor().assess(plan, (duplicate, duplicate))
