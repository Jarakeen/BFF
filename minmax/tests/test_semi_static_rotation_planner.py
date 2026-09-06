from models.build_model import PlayerBuild
from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_plan import RotationActionKind
from minmax.semi_static_rotation_planner import SemiStaticRotationPlanner


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        FrontBarSkills=[
            "Combat Prayer",
            "Radiating Regeneration",
            "",
            "",
            "",
            "Aggressive Horn",
        ],
        BackBarSkills=[
            "Overflowing Altar",
            "Expansive Frost Cloak",
            "",
            "",
            "",
            "Barrier",
        ],
        Potion="Essence of Spell Power",
    )


def test_rotation_definition_normalizes_editable_intent() -> None:
    definition = RotationDefinition(
        character_name="  Magrat  ",
        build_name=" DF Healer ",
        duration_seconds=10,
        action_interval_seconds=1,
        initial_bar=" FRONT ",
        mode="semi_static",
        steps=(
            RotationStep(kind="skill", name=" Combat Prayer ", bar=" FRONT "),
        ),
    )

    assert definition.character_name == "Magrat"
    assert definition.build_name == "DF Healer"
    assert definition.duration_seconds == 10.0
    assert definition.action_interval_seconds == 1.0
    assert definition.initial_bar == "front"
    assert definition.mode is RotationMode.SEMI_STATIC
    assert definition.steps[0].kind is RotationActionKind.SKILL
    assert definition.steps[0].name == "Combat Prayer"
    assert definition.steps[0].bar == "front"


def test_semi_static_planner_repeats_deterministically_with_explicit_bar_swaps() -> None:
    definition = RotationDefinition(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        action_interval_seconds=1.0,
        initial_bar="front",
        weave_light_attacks=True,
        steps=(
            RotationStep(
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationStep(kind=RotationActionKind.BAR_SWAP, bar="back"),
            RotationStep(
                kind=RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="back",
            ),
            RotationStep(kind=RotationActionKind.BAR_SWAP, bar="front"),
        ),
    )

    plan = SemiStaticRotationPlanner().build_plan(definition, _build())

    assert [
        (action.time_seconds, action.sequence, action.kind, action.name, action.bar)
        for action in plan.actions
    ] == [
        (0.0, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        (0.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        (1.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        (2.0, 0, RotationActionKind.LIGHT_ATTACK, None, "back"),
        (2.0, 1, RotationActionKind.SKILL, "Overflowing Altar", "back"),
        (3.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
        (4.0, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        (4.0, 1, RotationActionKind.SKILL, "Combat Prayer", "front"),
        (5.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
    ]
    assert plan.unresolved == ()
    assert any("repeat every 1s" in value for value in plan.assumptions)
    assert any("sub-GCD animation timing is unresolved" in value for value in plan.assumptions)


def test_semi_static_planner_keeps_invalid_saved_build_requests_explicit() -> None:
    definition = RotationDefinition(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=2.0,
        weave_light_attacks=False,
        steps=(
            RotationStep(
                kind=RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="back",
            ),
            RotationStep(
                kind=RotationActionKind.SKILL,
                name="Imaginary Skill",
                bar="front",
            ),
            RotationStep(
                kind=RotationActionKind.POTION,
                name="Imaginary Potion",
            ),
        ),
    )

    plan = SemiStaticRotationPlanner().build_plan(definition, _build())

    assert plan.actions == ()
    assert any("requires back bar but current bar is front" in value for value in plan.unresolved)
    assert any("Imaginary Skill" in value and "not present" in value for value in plan.unresolved)
    assert any("Imaginary Potion" in value and "does not match" in value for value in plan.unresolved)


def test_semi_static_planner_validates_ultimate_slot_and_saved_identity() -> None:
    planner = SemiStaticRotationPlanner()
    valid = RotationDefinition(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=0.0,
        weave_light_attacks=False,
        steps=(
            RotationStep(
                kind=RotationActionKind.ULTIMATE,
                name="Aggressive Horn",
                bar="front",
            ),
        ),
    )

    plan = planner.build_plan(valid, _build())
    assert [(action.kind, action.name, action.bar) for action in plan.actions] == [
        (RotationActionKind.ULTIMATE, "Aggressive Horn", "front")
    ]
    assert plan.unresolved == ()

    wrong_identity = RotationDefinition(
        character_name="Susan",
        build_name="DF Healer",
        duration_seconds=0.0,
        steps=(RotationStep(kind=RotationActionKind.WAIT),),
    )

    try:
        planner.build_plan(wrong_identity, _build())
    except ValueError as exc:
        assert "character identity" in str(exc)
    else:
        raise AssertionError("Expected cross-character rotation definition to be rejected")


def test_rotation_definition_rejects_invalid_modes_bars_and_empty_steps() -> None:
    invalid_definitions = (
        lambda: RotationDefinition(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=10,
            steps=(),
        ),
        lambda: RotationDefinition(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=10,
            action_interval_seconds=0,
            steps=(RotationStep(kind=RotationActionKind.WAIT),),
        ),
        lambda: RotationDefinition(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=10,
            mode="mystery",
            steps=(RotationStep(kind=RotationActionKind.WAIT),),
        ),
        lambda: RotationStep(
            kind=RotationActionKind.SKILL,
            name="Combat Prayer",
        ),
        lambda: RotationStep(
            kind=RotationActionKind.BAR_SWAP,
        ),
    )

    for create_value in invalid_definitions:
        try:
            create_value()
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid rotation definition input to be rejected")
