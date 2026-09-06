import pytest

from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=2.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(0.0, 1, RotationActionKind.SKILL, "Long Buff", "front"),
            RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(2.0, 1, RotationActionKind.SKILL, "Long Buff", "front"),
        ),
    )


def test_proven_heavy_attack_replaces_premature_recast_wait() -> None:
    contexts = []

    def decide(context):
        contexts.append(context)
        return RotationAction(
            time_seconds=context.time_seconds,
            sequence=context.slot.sequence,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Restoration Staff Heavy Attack",
            bar=context.bar,
        )

    refined = DurationAwareRotationScheduler().refine(
        _plan(),
        (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),),
        wait_decision=decide,
    )

    at_two = [action for action in refined.actions if action.time_seconds == 2.0]
    assert len(at_two) == 1
    assert at_two[0].kind is RotationActionKind.HEAVY_ATTACK
    assert at_two[0].bar == "front"
    assert len(contexts) == 1
    assert contexts[0].candidate.name == "Long Buff"
    assert contexts[0].next_due == (("long buff", "front", 10.0),)
    assert any("caller-proven heavy_attack decision" in item for item in refined.unresolved)


def test_wait_remains_when_decision_provider_declines() -> None:
    refined = DurationAwareRotationScheduler().refine(
        _plan(),
        (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),),
        wait_decision=lambda context: None,
    )

    at_two = [action for action in refined.actions if action.time_seconds == 2.0]
    assert len(at_two) == 1
    assert at_two[0].kind is RotationActionKind.WAIT


def test_wait_decision_cannot_cross_to_inactive_bar() -> None:
    def decide(context):
        return RotationAction(
            time_seconds=context.time_seconds,
            sequence=context.slot.sequence,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Ice Staff Heavy Attack",
            bar="back",
        )

    with pytest.raises(ValueError, match="active decision bar"):
        DurationAwareRotationScheduler().refine(
            _plan(),
            (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),),
            wait_decision=decide,
        )
