import math

from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
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


def test_persistent_rule_uses_never_due_scheduler_horizon() -> None:
    rule = RotationRecastRule(
        skill_name="Magical Banner",
        duration_seconds=None,
        bar="front",
        persistent=True,
    )

    assert rule.persistent is True
    assert math.isinf(float(rule.duration_seconds))
    assert DurationAwareRotationScheduler._refresh_due(0.0, rule) == math.inf


def test_persistent_rule_excludes_toggle_from_no_duration_filler_pool() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=2.0,
        actions=(
            _skill(0.0, "Magical Banner"),
            _skill(1.0, "Unnerving Boneyard"),
            _skill(2.0, "Unnerving Boneyard"),
        ),
    )
    rules = (
        RotationRecastRule(
            skill_name="Magical Banner",
            duration_seconds=None,
            bar="front",
            persistent=True,
        ),
        RotationRecastRule(
            skill_name="Unnerving Boneyard",
            duration_seconds=10.0,
            bar="front",
        ),
    )

    refined = DurationAwareRotationScheduler().refine(plan, rules)

    assert [
        action.name
        for action in refined.actions
        if action.kind is RotationActionKind.SKILL
    ] == ["Magical Banner", "Unnerving Boneyard"]
    assert any(
        action.kind is RotationActionKind.WAIT and action.time_seconds == 2.0
        for action in refined.actions
    )
    assert not any(
        "same-bar filler 'Magical Banner'" in item
        for item in refined.unresolved
    )
