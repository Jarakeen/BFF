from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_sustain_service import RotationSustainService


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=6.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(0.0, 1, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
            RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, name="Overflowing Altar", bar="back"),
            RotationAction(3.0, 0, RotationActionKind.WAIT, bar="back"),
        ),
        unresolved=("priority unresolved",),
    )


def test_named_actions_projects_only_named_skill_and_ultimate_actions() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=5.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(0.0, 1, RotationActionKind.SKILL, name="Combat Prayer", bar="front"),
            RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
            RotationAction(2.0, 0, RotationActionKind.ULTIMATE, name="Barrier", bar="back"),
            RotationAction(3.0, 0, RotationActionKind.POTION, name="Essence of Spell Power"),
            RotationAction(4.0, 0, RotationActionKind.WAIT, bar="back"),
        ),
    )

    actions = RotationSustainService.named_actions(plan)

    assert [(action.time_seconds, action.skill_name) for action in actions] == [
        (0.0, "Combat Prayer"),
        (2.0, "Barrier"),
    ]


def test_timeline_series_includes_initial_state_and_applied_event_states() -> None:
    run = SimpleNamespace(
        timeline=SimpleNamespace(
            starting_amount=30000,
            events=(
                SimpleNamespace(time_seconds=0.0, after=27500),
                SimpleNamespace(time_seconds=2.0, after=28500),
                SimpleNamespace(time_seconds=4.0, after=26000),
            ),
        )
    )

    assert RotationSustainService.timeline_series(run) == (
        (0.0, 30000.0),
        (0.0, 27500.0),
        (2.0, 28500.0),
        (4.0, 26000.0),
    )


def test_progression_infers_only_visibly_equipped_armor_lines_and_marks_boundary() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        AttributeHealth=0,
        AttributeMagicka=64,
        AttributeStamina=0,
    )
    build.Armor["Head"]["Weight"] = "light"
    build.Armor["Chest"]["Weight"] = "Heavy"
    build.Armor["Hands"]["Weight"] = ""

    progression, unresolved = RotationSustainService._progression(build)

    assert progression.attributes.magicka == 64
    assert progression.owned_skill_lines == ("Heavy Armor", "Light Armor")
    assert len(unresolved) == 1
    assert "infers equipped armor skill-line ownership" in unresolved[0]


def test_rotation_sustain_identity_requires_matching_character_and_build() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    RotationSustainService._validate_identity(build, _plan())

    wrong_character = RotationPlan(
        character_name="Susan",
        build_name="DF Healer",
        duration_seconds=1.0,
        actions=(),
    )
    try:
        RotationSustainService._validate_identity(build, wrong_character)
    except ValueError as exc:
        assert "character identity" in str(exc)
    else:
        raise AssertionError("Expected mismatched character identity to fail")

    wrong_build = RotationPlan(
        character_name="Magrat",
        build_name="Other Build",
        duration_seconds=1.0,
        actions=(),
    )
    try:
        RotationSustainService._validate_identity(build, wrong_build)
    except ValueError as exc:
        assert "build identity" in str(exc)
    else:
        raise AssertionError("Expected mismatched build identity to fail")
