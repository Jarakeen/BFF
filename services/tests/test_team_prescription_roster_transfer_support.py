from types import SimpleNamespace

from models.build_model import GearSlot, PlayerBuild
from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from ui.team_prescription_roster_transfer_support import (
    concise_prescription_preview,
    prescription_plan_slots,
)


def _page():
    tank = PlayerBuild(
        Name="Bone Tank",
        Gamertag="Tank Player",
        BuildName="YOUR TANK BUILD",
        EsoClass="Necromancer",
        Role="Tank",
        FrontBarWeapon=GearSlot(Set="Turning Tide"),
        BackBarWeapon=GearSlot(Set="Pearlescent Ward"),
    )
    scope = TeamPrescriptionScope(
        dimensions=(
            PrescriptionDimension.CLASS,
            PrescriptionDimension.BUILD,
            PrescriptionDimension.GEAR,
        )
    )
    prescription = PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=scope,
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Bone Tank",
                source_build_name="YOUR TANK BUILD",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name="Brittle Warden",
                prescribed_role="Healer",
                changes=(
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.CLASS,
                        current_value=None,
                        prescribed_value="Warden",
                        reason="Ranked template evidence selected this setup.",
                    ),
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.BUILD,
                        current_value=None,
                        prescribed_value="Brittle Warden",
                        reason="Ranked template evidence selected this setup.",
                    ),
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.GEAR,
                        current_value=None,
                        prescribed_value="Serpent's Disdain + Pillager's Profit",
                        reason="Ranked template evidence selected this setup.",
                    ),
                ),
                unresolved=("Healer 1: traits and enchants remain unresolved",),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=(
                    "DD 1: class, build, gear, skills, CP, Mundus, food, and potion remain unresolved",
                ),
            ),
        ),
        unresolved=(
            "DD 1: class, build, gear, skills, CP, Mundus, food, and potion remain unresolved",
        ),
    )
    return SimpleNamespace(
        roster=SimpleNamespace(Members=[tank]),
        current_prescription=prescription,
    )


def test_prescription_projection_preserves_saved_player_and_concrete_recruit_requirement() -> None:
    slots = prescription_plan_slots(_page())

    assert len(slots) == 3
    assert slots[0].kind == "saved"
    assert slots[0].player_name == "Bone Tank"
    assert slots[0].character_name == "Bone Tank"
    assert slots[0].eso_class == "Necromancer"
    assert slots[0].build_name == "YOUR TANK BUILD"
    assert "Turning Tide" in slots[0].gear_summary
    assert "Pearlescent Ward" in slots[0].gear_summary

    assert slots[1].kind == "prescribed_recruit"
    assert slots[1].player_name == "Recruitment Needed"
    assert slots[1].eso_class == "Warden"
    assert slots[1].build_name == "Brittle Warden"
    assert slots[1].gear_summary == "Serpent's Disdain + Pillager's Profit"
    assert "traits and enchants" in slots[1].unresolved

    assert slots[2].kind == "open_recruit"
    assert slots[2].eso_class == "Any class"
    assert slots[2].build_name == "Open requirement"


def test_concise_preview_stays_one_line_per_slot_instead_of_dumping_all_unresolved_text() -> None:
    page = _page()

    preview = concise_prescription_preview(page.current_prescription)

    assert "Main Tank: Bone Tank — YOUR TANK BUILD" in preview
    assert "Healer 1: RECRUIT — Warden • Brittle Warden" in preview
    assert "DD 1: RECRUIT — unresolved" in preview
    assert "Saved players: 1" in preview
    assert "Prescribed recruits: 1" in preview
    assert "Still unresolved: 1" in preview
    assert "class, build, gear, skills, CP" not in preview
