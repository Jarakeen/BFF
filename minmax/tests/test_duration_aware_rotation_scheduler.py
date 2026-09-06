from minmax.duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule


def _plan(actions, duration=12.0):
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _skill(time_seconds, name, bar="front", sequence=1):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def _la(time_seconds, bar="front"):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.LIGHT_ATTACK,
        bar=bar,
    )


def test_duration_skill_recasts_only_after_verified_expiry_and_uses_filler() -> None:
    plan = _plan(
        [
            _la(0.0),
            _skill(0.0, "Long Buff"),
            _la(1.0),
            _skill(1.0, "Filler"),
            _la(2.0),
            _skill(2.0, "Long Buff"),
            _la(3.0),
            _skill(3.0, "Filler"),
            _la(4.0),
            _skill(4.0, "Long Buff"),
            _la(5.0),
            _skill(5.0, "Filler"),
            _la(6.0),
            _skill(6.0, "Long Buff"),
        ],
        duration=6.0,
    )
    rule = RotationRecastRule("Long Buff", duration_seconds=5.0, bar="front")

    refined = DurationAwareRotationScheduler().refine(plan, (rule,))
    named = [
        (action.time_seconds, action.name)
        for action in refined.actions
        if action.kind is RotationActionKind.SKILL
    ]

    assert named == [
        (0.0, "Long Buff"),
        (1.0, "Filler"),
        (2.0, "Filler"),
        (3.0, "Filler"),
        (4.0, "Filler"),
        (5.0, "Filler"),
        (6.0, "Long Buff"),
    ]
    assert any("premature recast" in item for item in refined.unresolved)


def test_duration_scheduler_uses_deterministic_same_bar_filler_cycle() -> None:
    plan = _plan(
        [
            _skill(0.0, "Long Buff", sequence=0),
            _skill(1.0, "Filler A", sequence=0),
            _skill(2.0, "Filler B", sequence=0),
            _skill(3.0, "Long Buff", sequence=0),
            _skill(4.0, "Long Buff", sequence=0),
        ],
        duration=4.0,
    )
    rule = RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front")

    refined = DurationAwareRotationScheduler().refine(plan, (rule,))
    replacements = [
        action.name
        for action in refined.actions
        if action.kind is RotationActionKind.SKILL and action.time_seconds in {3.0, 4.0}
    ]

    assert replacements == ["Filler A", "Filler B"]


def test_duration_scheduler_preserves_explicit_bar_swap_and_never_crosses_fillers() -> None:
    plan = _plan(
        [
            _skill(0.0, "Front Buff", "front", 0),
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="back",
            ),
            _skill(2.0, "Back Filler", "back", 0),
            RotationAction(
                time_seconds=3.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="front",
            ),
            _skill(4.0, "Front Buff", "front", 0),
        ],
        duration=4.0,
    )
    rule = RotationRecastRule("Front Buff", duration_seconds=10.0, bar="front")

    refined = DurationAwareRotationScheduler().refine(plan, (rule,))

    swaps = [action for action in refined.actions if action.kind is RotationActionKind.BAR_SWAP]
    assert [(action.time_seconds, action.bar) for action in swaps] == [(1.0, "back"), (3.0, "front")]
    wait = next(action for action in refined.actions if action.time_seconds == 4.0)
    assert wait.kind is RotationActionKind.WAIT
    assert not any(
        action.time_seconds == 4.0 and action.name == "Back Filler"
        for action in refined.actions
    )


def test_wait_replaces_premature_recast_without_orphan_light_attack() -> None:
    plan = _plan(
        [
            _la(0.0),
            _skill(0.0, "Long Buff"),
            _la(2.0),
            _skill(2.0, "Long Buff"),
        ],
        duration=2.0,
    )
    rule = RotationRecastRule("Long Buff", duration_seconds=10.0, bar="front")

    refined = DurationAwareRotationScheduler().refine(plan, (rule,))

    at_two = [action for action in refined.actions if action.time_seconds == 2.0]
    assert len(at_two) == 1
    assert at_two[0].kind is RotationActionKind.WAIT


def test_duplicate_duration_rules_are_rejected() -> None:
    plan = _plan([_skill(0.0, "Buff", sequence=0)], duration=1.0)
    rules = (
        RotationRecastRule("Buff", duration_seconds=5.0, bar="front"),
        RotationRecastRule("Buff", duration_seconds=6.0, bar="front"),
    )

    try:
        DurationAwareRotationScheduler().refine(plan, rules)
    except ValueError as exc:
        assert "duplicate duration-aware rule" in str(exc)
    else:
        raise AssertionError("Expected duplicate duration rules to fail")
