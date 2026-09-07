from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.rotation_wait_decision import PrematureRecastDecision
from minmax.soft_action_duration_scheduler import SoftActionDurationRotationScheduler


def _skill(time_seconds, name, *, bar="front"):
    return RotationAction(
        time_seconds=float(time_seconds),
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def _plan(*actions, duration=6.0):
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=float(duration),
        actions=tuple(actions),
    )


def _heavy_decision(context):
    if context.time_seconds != 2.0:
        return None
    return PrematureRecastDecision(
        action=RotationAction(
            time_seconds=context.time_seconds,
            sequence=context.slot.sequence,
            kind=RotationActionKind.HEAVY_ATTACK,
            name="Heavy Attack",
            bar=context.bar,
        ),
        reservation_seconds=1.8,
    )


def test_proven_runtime_action_can_claim_soft_ordinary_skill_and_cascade_it() -> None:
    plan = _plan(
        _skill(0.0, "Long Buff"),
        _skill(2.0, "Filler A"),
        _skill(3.0, "Filler B"),
        _skill(4.0, "Filler C"),
        duration=4.0,
    )
    rules = (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),)

    refined = SoftActionDurationRotationScheduler().refine(
        plan,
        rules,
        soft_decision=_heavy_decision,
    )

    at_two = next(action for action in refined.actions if action.time_seconds == 2.0)
    assert at_two.kind is RotationActionKind.HEAVY_ATTACK
    assert not any(action.time_seconds == 3.0 for action in refined.actions)

    at_four = next(
        action
        for action in refined.actions
        if action.time_seconds == 4.0 and action.kind is RotationActionKind.SKILL
    )
    assert at_four.name == "Filler A"
    assert any("soft front-bar decision at 2s" in item for item in refined.unresolved)
    assert any("reserved the front-bar timeline through 3.8s" in item for item in refined.unresolved)
    assert any("Filler B" in item and "displaced beyond" in item for item in refined.unresolved)


def test_due_refresh_is_protected_before_soft_runtime_provider_is_consulted() -> None:
    calls = []

    def provider(context):
        calls.append(context.time_seconds)
        return PrematureRecastDecision(
            action=RotationAction(
                time_seconds=context.time_seconds,
                sequence=context.slot.sequence,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="Heavy Attack",
                bar=context.bar,
            ),
            reservation_seconds=1.8,
        )

    plan = _plan(
        _skill(0.0, "Buff"),
        _skill(2.0, "Buff"),
        duration=2.0,
    )
    rules = (RotationRecastRule("Buff", duration_seconds=2.0, bar="front"),)

    refined = SoftActionDurationRotationScheduler().refine(
        plan,
        rules,
        soft_decision=provider,
    )

    assert calls == []
    assert [
        (action.time_seconds, action.kind, action.name)
        for action in refined.actions
    ] == [
        (0.0, RotationActionKind.SKILL, "Buff"),
        (2.0, RotationActionKind.SKILL, "Buff"),
    ]


def test_premature_duration_recast_remains_optional_when_soft_action_replaces_it() -> None:
    plan = _plan(
        _skill(0.0, "Long Buff"),
        _skill(2.0, "Long Buff"),
        _skill(4.0, "Filler"),
        duration=4.0,
    )
    rules = (RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front"),)

    refined = SoftActionDurationRotationScheduler().refine(
        plan,
        rules,
        soft_decision=_heavy_decision,
    )

    assert any(
        action.time_seconds == 2.0 and action.kind is RotationActionKind.HEAVY_ATTACK
        for action in refined.actions
    )
    assert not any(
        item.startswith("skill 'Long Buff' was displaced beyond")
        for item in refined.unresolved
    )
