from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_sustain_projection import project_rotation_plan_to_sustain


def test_rotation_sustain_projection_emits_named_skill_actions_for_healer_plan() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=8.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=3.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="back",
            ),
            RotationAction(
                time_seconds=4.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Overflowing Altar",
                bar="back",
            ),
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.WAIT,
            ),
        ),
    )

    projection = project_rotation_plan_to_sustain(plan)

    assert [(action.time_seconds, action.skill_name) for action in projection.actions] == [
        (1.0, "Combat Prayer"),
        (4.0, "Overflowing Altar"),
    ]
    assert projection.unresolved == ()


def test_rotation_sustain_projection_preserves_plan_unknowns_and_resource_boundaries() -> None:
    plan = RotationPlan(
        character_name="Character",
        build_name="Build",
        duration_seconds=4.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.POTION,
                name="Essence of Spell Power",
            ),
            RotationAction(
                time_seconds=3.0,
                sequence=0,
                kind=RotationActionKind.ULTIMATE,
                name="Aggressive Horn",
                bar="back",
            ),
        ),
        unresolved=("cast time for Skill X is unknown",),
    )

    projection = project_rotation_plan_to_sustain(plan)

    assert projection.actions == ()
    assert projection.unresolved[0] == "cast time for Skill X is unknown"
    assert "verified weapon-specific heavy-attack inputs" in projection.unresolved[1]
    assert "canonical potion activation/restoration projection" in projection.unresolved[2]
    assert "does not model Ultimate resource spending" in projection.unresolved[3]
