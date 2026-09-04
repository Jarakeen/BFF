from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


def test_rotation_plan_orders_actions_deterministically() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="back",
            ),
        ),
        assumptions=("manual semi-static sequence",),
        unresolved=("cast time not yet projected",),
    )

    assert [(action.time_seconds, action.sequence) for action in plan.actions] == [
        (1.0, 0),
        (1.0, 1),
        (2.0, 0),
    ]
    assert plan.assumptions == ("manual semi-static sequence",)
    assert plan.unresolved == ("cast time not yet projected",)


def test_rotation_action_normalizes_names_bars_kinds_and_time() -> None:
    action = RotationAction(
        time_seconds=1,
        sequence=0,
        kind="skill",
        name="  Combat Prayer  ",
        bar=" FRONT ",
    )

    assert action.time_seconds == 1.0
    assert action.kind is RotationActionKind.SKILL
    assert action.name == "Combat Prayer"
    assert action.bar == "front"


def test_rotation_plan_rejects_ambiguous_same_time_ordering() -> None:
    actions = (
        RotationAction(
            time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Skill A",
        ),
        RotationAction(
            time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
        ),
    )

    try:
        RotationPlan(
            character_name="Character",
            build_name="Build",
            duration_seconds=2.0,
            actions=actions,
        )
    except ValueError as exc:
        assert "distinct sequence values" in str(exc)
    else:
        raise AssertionError("Expected ambiguous same-time rotation ordering to be rejected")


def test_rotation_contract_rejects_invalid_identity_timing_and_action_requirements() -> None:
    invalid_actions = (
        lambda: RotationAction(
            time_seconds=-1.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
        ),
        lambda: RotationAction(
            time_seconds=0.0,
            sequence=-1,
            kind=RotationActionKind.LIGHT_ATTACK,
        ),
        lambda: RotationAction(
            time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
        ),
        lambda: RotationAction(
            time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.BAR_SWAP,
        ),
        lambda: RotationAction(
            time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
            bar="side",
        ),
        lambda: RotationAction(
            time_seconds=0.0,
            sequence=0,
            kind="dance",
        ),
    )

    for create_action in invalid_actions:
        try:
            create_action()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid rotation action to be rejected")

    valid_action = RotationAction(
        time_seconds=2.0,
        sequence=0,
        kind=RotationActionKind.LIGHT_ATTACK,
    )
    invalid_plans = (
        {"character_name": "", "build_name": "Build", "duration_seconds": 2.0},
        {"character_name": "Character", "build_name": "", "duration_seconds": 2.0},
        {"character_name": "Character", "build_name": "Build", "duration_seconds": -1.0},
        {"character_name": "Character", "build_name": "Build", "duration_seconds": 1.0},
    )

    for kwargs in invalid_plans:
        try:
            RotationPlan(actions=(valid_action,), **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid rotation plan to be rejected: {kwargs}")
