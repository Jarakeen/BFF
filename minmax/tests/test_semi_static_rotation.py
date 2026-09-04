from minmax.rotation_plan import RotationActionKind
from minmax.semi_static_rotation import (
    SemiStaticRotationEntry,
    create_semi_static_rotation_plan,
)


def test_semi_static_healer_plan_expands_explicit_recasts_deterministically() -> None:
    plan = create_semi_static_rotation_plan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=20.0,
        entries=(
            SemiStaticRotationEntry(
                first_time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
                recast_interval_seconds=8.0,
            ),
            SemiStaticRotationEntry(
                first_time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="back",
                recast_interval_seconds=15.0,
            ),
        ),
    )

    assert [
        (action.time_seconds, action.sequence, action.name, action.bar)
        for action in plan.actions
    ] == [
        (0.0, 0, "Combat Prayer", "front"),
        (1.0, 1, "Overflowing Altar", "back"),
        (8.0, 0, "Combat Prayer", "front"),
        (16.0, 0, "Combat Prayer", "front"),
        (16.0, 1, "Overflowing Altar", "back"),
    ]
    assert len(plan.assumptions) == 1
    assert "caller-supplied assumptions" in plan.assumptions[0]


def test_semi_static_plan_supports_one_shot_actions_without_recast_assumption() -> None:
    plan = create_semi_static_rotation_plan(
        character_name="Character",
        build_name="Build",
        duration_seconds=5.0,
        entries=(
            SemiStaticRotationEntry(
                first_time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="back",
            ),
        ),
        assumptions=("manual opener",),
    )

    assert [(action.time_seconds, action.kind, action.bar) for action in plan.actions] == [
        (2.0, RotationActionKind.BAR_SWAP, "back")
    ]
    assert plan.assumptions == ("manual opener",)


def test_semi_static_entry_rejects_invalid_timing_and_recast() -> None:
    invalid_entries = (
        lambda: SemiStaticRotationEntry(
            first_time_seconds=-1.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
        ),
        lambda: SemiStaticRotationEntry(
            first_time_seconds=0.0,
            sequence=-1,
            kind=RotationActionKind.LIGHT_ATTACK,
        ),
        lambda: SemiStaticRotationEntry(
            first_time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.LIGHT_ATTACK,
            recast_interval_seconds=0.0,
        ),
    )

    for create_entry in invalid_entries:
        try:
            create_entry()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid semi-static entry to be rejected")


def test_semi_static_plan_rejects_same_timestamp_sequence_collision() -> None:
    entries = (
        SemiStaticRotationEntry(
            first_time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Skill A",
        ),
        SemiStaticRotationEntry(
            first_time_seconds=1.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Skill B",
        ),
    )

    try:
        create_semi_static_rotation_plan(
            character_name="Character",
            build_name="Build",
            duration_seconds=2.0,
            entries=entries,
        )
    except ValueError as exc:
        assert "distinct sequence values" in str(exc)
    else:
        raise AssertionError("Expected ambiguous same-time semi-static actions to be rejected")
