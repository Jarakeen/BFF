from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import (
    RotationPotionCadenceAssessor,
    RotationPotionCadenceRequirement,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=120.0,
        actions=tuple(actions),
    )


def test_potion_cadence_accepts_exact_boundary() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.POTION, "Essence of Spell Power"),
        RotationAction(45.0, 0, RotationActionKind.POTION, "Essence of Spell Power"),
    )

    result = RotationPotionCadenceAssessor().assess(
        plan,
        RotationPotionCadenceRequirement(45.0),
    )

    assert result.legal
    assert result.violations == ()


def test_potion_cadence_is_shared_across_different_potion_names() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.POTION, "Essence of Spell Power"),
        RotationAction(30.0, 0, RotationActionKind.POTION, "Essence of Health"),
    )

    result = RotationPotionCadenceAssessor().assess(
        plan,
        RotationPotionCadenceRequirement(45.0),
    )

    assert not result.legal
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.previous_name == "Essence of Spell Power"
    assert violation.action_name == "Essence of Health"
    assert violation.actual_interval_seconds == 30.0
    assert violation.required_interval_seconds == 45.0


def test_potion_cadence_uses_consecutive_use_history_after_violation() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.POTION, "Potion A"),
        RotationAction(20.0, 0, RotationActionKind.POTION, "Potion B"),
        RotationAction(50.0, 0, RotationActionKind.POTION, "Potion C"),
    )

    result = RotationPotionCadenceAssessor().assess(
        plan,
        RotationPotionCadenceRequirement(45.0),
    )

    assert [(item.previous_time_seconds, item.time_seconds) for item in result.violations] == [
        (0.0, 20.0),
        (20.0, 50.0),
    ]
