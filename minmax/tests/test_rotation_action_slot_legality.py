from minmax.rotation_action_slot_legality import (
    RotationActionSlotAssessor,
    RotationActionSlotRequirement,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=tuple(actions),
    )


def test_slot_legality_accepts_only_bars_where_action_is_slotted() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Front Heal", "front"),
        RotationAction(12.0, 0, RotationActionKind.SKILL, "Front Heal", "back"),
        RotationAction(14.0, 0, RotationActionKind.SKILL, "Shared Skill", "back"),
    )
    requirements = (
        RotationActionSlotRequirement("Front Heal", ("front",)),
        RotationActionSlotRequirement("Shared Skill", ("front", "back")),
    )

    result = RotationActionSlotAssessor().assess(plan, requirements)

    assert not result.legal
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.requirement.action_name == "Front Heal"
    assert violation.scheduled_bar == "back"
    assert violation.reason == "action is not slotted on the scheduled bar"


def test_slot_legality_treats_missing_action_bar_as_violation_when_slot_evidence_exists() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Front Ultimate"),
    )
    requirement = RotationActionSlotRequirement(
        "Front Ultimate",
        ("front",),
        action_kind=RotationActionKind.ULTIMATE,
    )

    result = RotationActionSlotAssessor().assess(plan, (requirement,))

    assert not result.legal
    assert result.violations[0].scheduled_bar is None
    assert result.violations[0].reason == "scheduled action has no explicit bar"


def test_slot_legality_ignores_actions_without_supplied_slot_evidence() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.SKILL, "Unknown Skill", "back"),
    )

    result = RotationActionSlotAssessor().assess(plan, ())

    assert result.legal
    assert result.violations == ()
