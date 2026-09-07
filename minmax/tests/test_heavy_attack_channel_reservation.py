import pytest

from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecision


def _skill(time_seconds, name, bar="front") -> RotationAction:
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def _reservation_provider(context):
    return PrematureRecastDecision(
        action=RotationAction(
            time_seconds=context.time_seconds,
            sequence=context.slot.sequence,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Restoration Staff Heavy Attack",
            bar=context.bar,
        ),
        reservation_seconds=1.8,
    )


def test_heavy_channel_reservation_displaces_covered_same_bar_skill_forward() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="RO Healer",
        duration_seconds=5.0,
        actions=(
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            _skill(3.0, "Action A"),
            _skill(4.0, "Action B"),
            _skill(5.0, "Action C"),
        ),
    )
    rules = (
        RotationRecastRule("Long Buff", 10.0, bar="front"),
        RotationRecastRule("Action A", 20.0, bar="front"),
        RotationRecastRule("Action B", 20.0, bar="front"),
        RotationRecastRule("Action C", 20.0, bar="front"),
    )

    refined = DurationAwareRotationScheduler().refine(
        plan,
        rules,
        wait_decision=_reservation_provider,
    )

    at_two = next(action for action in refined.actions if action.time_seconds == 2.0)
    assert at_two.kind is RotationActionKind.HEAVY_ATTACK

    assert not any(action.time_seconds == 3.0 for action in refined.actions)

    at_four = next(
        action
        for action in refined.actions
        if action.time_seconds == 4.0 and action.kind is RotationActionKind.SKILL
    )
    assert at_four.name == "Action A"

    at_five = next(
        action
        for action in refined.actions
        if action.time_seconds == 5.0 and action.kind is RotationActionKind.SKILL
    )
    assert at_five.name == "Action B"

    assert any("reserved the front-bar timeline through 3.8s" in item for item in refined.unresolved)
    assert any("Action A" in item and "displaced by" in item for item in refined.unresolved)
    assert any("Action C" in item and "displaced beyond" in item for item in refined.unresolved)


def test_heavy_channel_reservation_cannot_cross_bar_swap() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="RO Healer",
        duration_seconds=4.0,
        actions=(
            _skill(0.0, "Long Buff"),
            _skill(2.0, "Long Buff"),
            RotationAction(3.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _skill(4.0, "Back Skill", bar="back"),
        ),
    )
    rules = (
        RotationRecastRule("Long Buff", 10.0, bar="front"),
        RotationRecastRule("Back Skill", 20.0, bar="back"),
    )

    with pytest.raises(ValueError, match="hard timeline boundary"):
        DurationAwareRotationScheduler().refine(
            plan,
            rules,
            wait_decision=_reservation_provider,
        )
