from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_ultimate import UltimateRotationScheduler, UltimateScheduleRule


def _plan(actions, duration=10.0):
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _skill(time_seconds, name, bar="front"):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
    )


def test_explicit_ultimate_availability_claims_first_same_bar_skill_slot() -> None:
    plan = _plan(
        [
            _skill(0.0, "Front Skill", "front"),
            _skill(1.0, "Front Skill", "front"),
            _skill(2.0, "Front Skill", "front"),
        ],
        duration=2.0,
    )
    rule = UltimateScheduleRule(
        "Aggressive Horn",
        bar="front",
        cost=250.0,
        available_at_seconds=(1.0,),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))

    at_one = next(action for action in result.actions if action.time_seconds == 1.0)
    assert at_one.kind is RotationActionKind.ULTIMATE
    assert at_one.name == "Aggressive Horn"
    assert at_one.bar == "front"
    assert any("claimed the 1s" in item for item in result.unresolved)


def test_displaced_skill_cascades_to_next_same_bar_slot() -> None:
    plan = _plan(
        [
            _skill(0.0, "A"),
            _skill(1.0, "B"),
            _skill(2.0, "C"),
            _skill(3.0, "D"),
        ],
        duration=3.0,
    )
    rule = UltimateScheduleRule(
        "Guardian's Wrath",
        bar="front",
        cost=75.0,
        available_at_seconds=(1.0,),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))

    by_time = {action.time_seconds: action for action in result.actions}
    assert by_time[1.0].kind is RotationActionKind.ULTIMATE
    assert by_time[1.0].name == "Guardian's Wrath"
    assert by_time[2.0].name == "B"
    assert by_time[3.0].name == "C"
    assert any("skill 'D' was displaced beyond the 3s plan horizon" in item for item in result.unresolved)


def test_displacement_cascade_never_crosses_bars() -> None:
    plan = _plan(
        [
            _skill(0.0, "Front A", "front"),
            _skill(1.0, "Front B", "front"),
            _skill(2.0, "Back A", "back"),
            _skill(3.0, "Front C", "front"),
        ],
        duration=3.0,
    )
    rule = UltimateScheduleRule(
        "Guardian's Wrath",
        bar="front",
        cost=75.0,
        available_at_seconds=(1.0,),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))

    by_time = {action.time_seconds: action for action in result.actions}
    assert by_time[2.0].name == "Back A"
    assert by_time[2.0].bar == "back"
    assert by_time[3.0].name == "Front B"
    assert by_time[3.0].bar == "front"
    assert any("skill 'Front C' was displaced beyond the 3s plan horizon" in item for item in result.unresolved)


def test_ultimate_never_crosses_to_wrong_bar() -> None:
    plan = _plan(
        [
            _skill(0.0, "Back Skill", "back"),
            _skill(1.0, "Back Skill", "back"),
            _skill(2.0, "Front Skill", "front"),
        ],
        duration=2.0,
    )
    rule = UltimateScheduleRule(
        "Aggressive Horn",
        bar="front",
        cost=250.0,
        available_at_seconds=(0.0,),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))

    assert all(
        not (action.kind is RotationActionKind.ULTIMATE and action.bar == "back")
        for action in result.actions
    )
    at_two = next(action for action in result.actions if action.time_seconds == 2.0)
    assert at_two.kind is RotationActionKind.ULTIMATE
    assert at_two.name == "Aggressive Horn"


def test_multiple_explicit_availability_events_claim_multiple_slots() -> None:
    plan = _plan(
        [
            _skill(0.0, "Skill"),
            _skill(1.0, "Skill"),
            _skill(2.0, "Skill"),
            _skill(3.0, "Skill"),
            _skill(4.0, "Skill"),
        ],
        duration=4.0,
    )
    rule = UltimateScheduleRule(
        "Aggressive Horn",
        bar="front",
        cost=250.0,
        available_at_seconds=(1.0, 3.0),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))
    casts = [
        action.time_seconds
        for action in result.actions
        if action.kind is RotationActionKind.ULTIMATE
    ]

    assert casts == [1.0, 3.0]


def test_unplaceable_explicit_availability_remains_unresolved() -> None:
    plan = _plan([_skill(0.0, "Front Skill", "front")], duration=5.0)
    rule = UltimateScheduleRule(
        "Aggressive Horn",
        bar="front",
        cost=250.0,
        available_at_seconds=(4.0,),
    )

    result = UltimateRotationScheduler().apply(plan, (rule,))

    assert not any(action.kind is RotationActionKind.ULTIMATE for action in result.actions)
    assert any("no eligible front-bar skill slot remained" in item for item in result.unresolved)


def test_invalid_or_duplicate_ultimate_rules_are_rejected() -> None:
    try:
        UltimateScheduleRule("Horn", bar="front", cost=0.0, available_at_seconds=(0.0,))
    except ValueError as exc:
        assert "cost" in str(exc)
    else:
        raise AssertionError("Expected zero-cost ultimate rule to fail")

    plan = _plan([_skill(0.0, "Skill")], duration=1.0)
    rules = (
        UltimateScheduleRule("Horn", "front", 250.0, (0.0,)),
        UltimateScheduleRule("Horn", "front", 250.0, (1.0,)),
    )
    try:
        UltimateRotationScheduler().apply(plan, rules)
    except ValueError as exc:
        assert "duplicate ultimate schedule rule" in str(exc)
    else:
        raise AssertionError("Expected duplicate ultimate rules to fail")
