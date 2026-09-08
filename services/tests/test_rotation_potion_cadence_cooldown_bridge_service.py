from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_potion_cadence import RotationPotionCadenceRequirement
from services.rotation_potion_cadence_cooldown_bridge_service import (
    RotationPotionCadenceCooldownBridgeService,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=120.0,
        actions=tuple(actions),
    )


def test_shared_potion_cadence_projects_to_hard_cooldown_violation() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.POTION, "Essence of Spell Power"),
        RotationAction(30.0, 0, RotationActionKind.POTION, "Essence of Health"),
    )

    result = RotationPotionCadenceCooldownBridgeService().assess(
        plan,
        RotationPotionCadenceRequirement(45.0),
    )

    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.requirement.action_kind is RotationActionKind.POTION
    assert violation.requirement.action_name == "Essence of Health"
    assert violation.actual_interval_seconds == 30.0
    assert violation.required_interval_seconds == 45.0
