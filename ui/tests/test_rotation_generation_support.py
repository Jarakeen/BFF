from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.rotation_plan import RotationActionKind
from ui.rotation_generation_support import (
    RotationGenerationRequest,
    RotationGenerationSupport,
)


def _build() -> PlayerBuild:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Potion="Essence of Spell Power",
    )
    build.FrontBarSkills = [
        "Combat Prayer",
        "Radiating Regeneration",
        "Energy Orb",
        "",
        "",
        "Aggressive Horn",
    ]
    build.BackBarSkills = [
        "Overflowing Altar",
        "Expansive Frost Cloak",
        "",
        "",
        "",
        "Barrier",
    ]
    return build


def test_dashboard_seed_definition_uses_saved_ordinary_bar_order() -> None:
    definition = RotationGenerationSupport().build_definition(
        build=_build(),
        request=RotationGenerationRequest(),
    )

    assert [(step.kind, step.name, step.bar) for step in definition.steps] == [
        (RotationActionKind.SKILL, "Combat Prayer", "front"),
        (RotationActionKind.SKILL, "Radiating Regeneration", "front"),
        (RotationActionKind.SKILL, "Energy Orb", "front"),
        (RotationActionKind.BAR_SWAP, None, "back"),
        (RotationActionKind.SKILL, "Overflowing Altar", "back"),
        (RotationActionKind.SKILL, "Expansive Frost Cloak", "back"),
        (RotationActionKind.BAR_SWAP, None, "front"),
    ]
    assert definition.initial_bar == "front"
    assert any("priority" in item for item in definition.unresolved)
    assert any("ultimate" in item for item in definition.unresolved)
    assert any("canonical positive skill durations" in item for item in definition.assumptions)


def test_dashboard_generation_produces_real_rotation_plan() -> None:
    plan = RotationGenerationSupport().generate(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=6.0),
    )

    assert plan.character_name == "Magrat"
    assert plan.build_name == "DF Healer"
    assert plan.duration_seconds == 6.0
    assert plan.actions[0].kind is RotationActionKind.LIGHT_ATTACK
    assert plan.actions[1].kind is RotationActionKind.SKILL
    assert plan.actions[1].name == "Combat Prayer"
    assert any(action.kind is RotationActionKind.BAR_SWAP for action in plan.actions)


def test_dashboard_generation_returns_duration_refined_plan() -> None:
    calls = []

    class RefinementStub:
        def refine(self, plan):
            calls.append(plan)
            return SimpleNamespace(plan=plan)

    support = RotationGenerationSupport(duration_refinement=RefinementStub())
    plan = support.generate(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=6.0),
    )

    assert calls == [plan]


def test_dashboard_generation_rejects_modes_not_yet_implemented() -> None:
    support = RotationGenerationSupport()
    for value in ("Static", "Dynamic"):
        try:
            support.generate(
                build=_build(),
                request=RotationGenerationRequest(rotation_type=value),
            )
        except ValueError as exc:
            assert "currently generates only Semi-static" in str(exc)
        else:
            raise AssertionError(f"Expected unsupported dashboard mode to fail: {value}")


def test_dashboard_generation_keeps_potion_cadence_explicitly_unresolved() -> None:
    definition = RotationGenerationSupport().build_definition(
        build=_build(),
        request=RotationGenerationRequest(
            potion="Essence of Spell Power",
            potion_on_cooldown=True,
        ),
    )

    assert any("potion-on-cooldown cadence" in item for item in definition.unresolved)
    assert not any(step.kind is RotationActionKind.POTION for step in definition.steps)


def test_dashboard_generation_rejects_build_without_ordinary_skills() -> None:
    build = PlayerBuild(Name="Magrat", BuildName="Empty")
    build.FrontBarSkills = ["", "", "", "", "", "Aggressive Horn"]
    build.BackBarSkills = ["", "", "", "", "", "Barrier"]

    try:
        RotationGenerationSupport().generate(
            build=build,
            request=RotationGenerationRequest(),
        )
    except ValueError as exc:
        assert "no ordinary slotted skills" in str(exc)
    else:
        raise AssertionError("Expected empty ordinary bars to be rejected")
