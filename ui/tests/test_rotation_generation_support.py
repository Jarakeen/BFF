from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.rotation_ability_priority import AbilityPriorityEntry
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


def test_dashboard_seed_definition_honors_explicit_ability_priorities() -> None:
    priorities = (
        AbilityPriorityEntry("front", 1, "Combat Prayer", 20),
        AbilityPriorityEntry("front", 2, "Radiating Regeneration", 30),
        AbilityPriorityEntry("front", 3, "Energy Orb", 10),
        AbilityPriorityEntry("back", 1, "Overflowing Altar", 20),
        AbilityPriorityEntry("back", 2, "Expansive Frost Cloak", 10),
    )

    definition = RotationGenerationSupport().build_definition(
        build=_build(),
        request=RotationGenerationRequest(ability_priorities=priorities),
    )

    assert [(step.kind, step.name, step.bar) for step in definition.steps] == [
        (RotationActionKind.SKILL, "Energy Orb", "front"),
        (RotationActionKind.SKILL, "Combat Prayer", "front"),
        (RotationActionKind.SKILL, "Radiating Regeneration", "front"),
        (RotationActionKind.BAR_SWAP, None, "back"),
        (RotationActionKind.SKILL, "Expansive Frost Cloak", "back"),
        (RotationActionKind.SKILL, "Overflowing Altar", "back"),
        (RotationActionKind.BAR_SWAP, None, "front"),
    ]
    assert not any("ability-priority editing" in item for item in definition.unresolved)
    assert any("explicit ability priority values" in item for item in definition.assumptions)


def test_dashboard_seed_definition_rejects_incomplete_explicit_priorities() -> None:
    try:
        RotationGenerationSupport().build_definition(
            build=_build(),
            request=RotationGenerationRequest(
                ability_priorities=(
                    AbilityPriorityEntry("front", 1, "Combat Prayer", 10),
                )
            ),
        )
    except ValueError as exc:
        assert "ability priority is missing" in str(exc)
    else:
        raise AssertionError("Expected incomplete explicit priorities to fail")


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
    refinement_calls = []
    projection = SimpleNamespace(label="final projection")
    evidence = SimpleNamespace(summary="duration evidence")

    class RefinementStub:
        def refine(self, plan):
            refinement_calls.append(plan)
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class EvidenceStub:
        def from_projection(self, received):
            assert received is projection
            return evidence

    support = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
    )
    plan = support.generate(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=6.0),
    )

    assert refinement_calls == [plan]


def test_dashboard_generation_can_return_plan_with_duration_evidence() -> None:
    projection = SimpleNamespace(label="verified projection")
    evidence = SimpleNamespace(summary="verified durations")
    evidence_calls = []

    class RefinementStub:
        def refine(self, plan):
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class EvidenceStub:
        def from_projection(self, received):
            evidence_calls.append(received)
            return evidence

    result = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
    ).generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=6.0),
    )

    assert result.plan.character_name == "Magrat"
    assert result.plan.build_name == "DF Healer"
    assert result.duration_evidence is evidence
    assert result.ultimate_projection is None
    assert evidence_calls == [projection]


def test_dashboard_generation_applies_selected_ultimate_and_rebuilds_final_evidence() -> None:
    projection = SimpleNamespace(label="duration-refined projection")
    final_evidence = SimpleNamespace(summary="post-ultimate evidence")
    ultimate_calls = []
    build_calls = []

    class RefinementStub:
        def refine(self, plan):
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class UltimateStub:
        def apply_generation(self, **kwargs):
            ultimate_calls.append(kwargs)
            return SimpleNamespace(plan=kwargs["plan"], rules=("ultimate rule",))

    class EvidenceStub:
        def from_projection(self, received):
            raise AssertionError("post-ultimate generation must re-analyze the final plan")

        def build(self, plan):
            build_calls.append(plan)
            return final_evidence

    result = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
        ultimate_service=UltimateStub(),
    ).generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(
            duration_seconds=6.0,
            ultimate_bar="front",
            starting_ultimate=120.0,
            use_scheduled_combat_attacks_for_ultimate=True,
        ),
    )

    assert len(ultimate_calls) == 1
    assert ultimate_calls[0]["ultimate_bar"] == "front"
    assert ultimate_calls[0]["starting_ultimate"] == 120.0
    assert ultimate_calls[0]["use_scheduled_combat_attacks"] is True
    assert build_calls == [result.plan]
    assert result.duration_evidence is final_evidence
    assert result.ultimate_projection.rules == ("ultimate rule",)


def test_dashboard_generation_leaves_ultimate_unscheduled_without_bar_selection() -> None:
    projection = SimpleNamespace(label="verified projection")
    evidence = SimpleNamespace(summary="verified durations")

    class RefinementStub:
        def refine(self, plan):
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class UltimateStub:
        def apply_generation(self, **kwargs):
            raise AssertionError("blank ultimate selection must not project Ultimate")

    class EvidenceStub:
        def from_projection(self, received):
            assert received is projection
            return evidence

    result = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
        ultimate_service=UltimateStub(),
    ).generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(duration_seconds=6.0),
    )

    assert result.duration_evidence is evidence
    assert result.ultimate_projection is None
    assert any("no ultimate bar is selected" in item for item in result.plan.unresolved)


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
