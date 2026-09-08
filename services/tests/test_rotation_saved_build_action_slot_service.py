from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from services.rotation_saved_build_action_slot_service import (
    RotationSavedBuildActionSlotService,
)


def _build(front, back=()):
    return SimpleNamespace(
        FrontBarSkills=tuple(front),
        BackBarSkills=tuple(back),
    )


def test_saved_build_slot_service_resolves_front_back_and_shared_skills() -> None:
    build = _build(
        ("Front Heal", "Shared Skill", "", "", "", "Front Ultimate"),
        ("Back Skill", "Shared Skill", "", "", "", "Back Ultimate"),
    )

    evidence = RotationSavedBuildActionSlotService().resolve(build)

    resolved = {
        (item.action_kind, item.action_name): item.allowed_bars
        for item in evidence.slot_requirements
    }
    assert resolved[(RotationActionKind.SKILL, "Front Heal")] == ("front",)
    assert resolved[(RotationActionKind.SKILL, "Back Skill")] == ("back",)
    assert resolved[(RotationActionKind.SKILL, "Shared Skill")] == ("front", "back")
    assert resolved[(RotationActionKind.ULTIMATE, "Front Ultimate")] == ("front",)
    assert resolved[(RotationActionKind.ULTIMATE, "Back Ultimate")] == ("back",)
    assert evidence.unresolved == ()


def test_saved_build_slot_service_dedupes_repeated_same_bar_skill() -> None:
    build = _build(("Shared Skill", "Shared Skill"))

    evidence = RotationSavedBuildActionSlotService().resolve(build)

    assert len(evidence.slot_requirements) == 1
    assert evidence.slot_requirements[0].allowed_bars == ("front",)


def test_saved_build_slot_service_marks_same_name_skill_and_ultimate_ambiguous() -> None:
    build = _build(
        ("Ambiguous Action", "", "", "", "", "Front Ultimate"),
        ("Back Skill", "", "", "", "", "Ambiguous Action"),
    )

    evidence = RotationSavedBuildActionSlotService().resolve(build)

    resolved_names = {item.action_name for item in evidence.slot_requirements}
    assert "Ambiguous Action" not in resolved_names
    assert "Front Ultimate" in resolved_names
    assert "Back Skill" in resolved_names
    assert evidence.unresolved == (
        "saved-build action slot identity is ambiguous because 'Ambiguous Action' "
        "appears as both skill and ultimate",
    )


def test_saved_build_slot_service_tolerates_minimal_test_doubles() -> None:
    evidence = RotationSavedBuildActionSlotService().resolve(object())

    assert evidence.slot_requirements == ()
    assert evidence.unresolved == ()
