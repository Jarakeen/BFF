from __future__ import annotations

import pytest

from minmax.rotation_action_target_legality import (
    RotationActionTargetAssessor,
    RotationActionTargetRequirement,
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_target_legality_rejects_wrong_explicit_target_kind() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    requirement = RotationActionTargetRequirement(
        action_name="Combat Prayer",
        allowed_targets=(RotationTargetKind.ALLY,),
        bar="front",
    )
    windows = (
        RotationTargetStateWindow("Group stack", 9.0, 11.0, RotationTargetKind.ALLY),
        RotationTargetStateWindow("Boss target", 19.0, 21.0, RotationTargetKind.ENEMY),
    )

    result = RotationActionTargetAssessor().assess(plan, (requirement,), windows)

    assert not result.legal
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.time_seconds == 20.0
    assert violation.observed_target is RotationTargetKind.ENEMY
    assert "expected one of: ally" in violation.reason


def test_target_legality_supports_multiple_allowed_targets_and_explicit_windows_only() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Support Skill", "front"),
        RotationAction(30.0, 0, RotationActionKind.SKILL, "Support Skill", "front"),
    )
    requirement = RotationActionTargetRequirement(
        action_name="Support Skill",
        allowed_targets=(RotationTargetKind.SELF, RotationTargetKind.ALLY),
    )

    result = RotationActionTargetAssessor().assess(
        plan,
        (requirement,),
        (RotationTargetStateWindow("Self cast", 9.0, 11.0, RotationTargetKind.SELF),),
    )

    assert result.legal
    assert result.violations == ()


def test_weapon_attacks_are_kind_identified_and_can_require_enemy_target() -> None:
    plan = _plan(
        RotationAction(5.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
        RotationAction(15.0, 0, RotationActionKind.HEAVY_ATTACK, bar="front"),
    )
    requirements = (
        RotationActionTargetRequirement(
            action_kind=RotationActionKind.LIGHT_ATTACK,
            allowed_targets=(RotationTargetKind.ENEMY,),
            bar="front",
        ),
        RotationActionTargetRequirement(
            action_kind=RotationActionKind.HEAVY_ATTACK,
            allowed_targets=(RotationTargetKind.ENEMY,),
            bar="front",
        ),
    )
    windows = (
        RotationTargetStateWindow("Enemy", 4.0, 6.0, RotationTargetKind.ENEMY),
        RotationTargetStateWindow("Ground", 14.0, 16.0, RotationTargetKind.GROUND),
    )

    result = RotationActionTargetAssessor().assess(plan, requirements, windows)

    assert not result.legal
    assert len(result.violations) == 1
    assert result.violations[0].requirement.action_kind is RotationActionKind.HEAVY_ATTACK
    assert result.violations[0].observed_target is RotationTargetKind.GROUND


def test_target_requirement_validation_fails_closed() -> None:
    with pytest.raises(ValueError, match="at least one allowed target"):
        RotationActionTargetRequirement(
            action_name="Skill",
            allowed_targets=(),
        )

    with pytest.raises(ValueError, match="needs action_name"):
        RotationActionTargetRequirement(
            allowed_targets=(RotationTargetKind.ENEMY,),
        )

    with pytest.raises(ValueError, match="must not set action_name"):
        RotationActionTargetRequirement(
            action_name="Light Attack",
            action_kind=RotationActionKind.LIGHT_ATTACK,
            allowed_targets=(RotationTargetKind.ENEMY,),
        )

    with pytest.raises(ValueError, match="support skill, ultimate, light attack, or heavy attack"):
        RotationActionTargetRequirement(
            action_kind=RotationActionKind.POTION,
            allowed_targets=(RotationTargetKind.SELF,),
        )


def test_duplicate_requirements_and_overlapping_target_windows_fail_closed() -> None:
    requirement = RotationActionTargetRequirement(
        action_name="Skill",
        allowed_targets=(RotationTargetKind.ENEMY,),
    )
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Skill", "front"),
    )

    with pytest.raises(ValueError, match="duplicate rotation target requirement"):
        RotationActionTargetAssessor().assess(
            plan,
            (requirement, requirement),
            (RotationTargetStateWindow("Enemy", 9.0, 11.0, RotationTargetKind.ENEMY),),
        )

    with pytest.raises(ValueError, match="cannot overlap"):
        RotationActionTargetAssessor().assess(
            plan,
            (requirement,),
            (
                RotationTargetStateWindow("First", 9.0, 12.0, RotationTargetKind.ENEMY),
                RotationTargetStateWindow("Second", 11.0, 13.0, RotationTargetKind.ENEMY),
            ),
        )
