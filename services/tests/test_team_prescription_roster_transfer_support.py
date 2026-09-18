from pathlib import Path
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
    assert slots[0].role == "Tank"
    assert slots[0].source_kind == "optimizer_prescription"
    assert slots[0].gear_sets == ("Turning Tide", "Pearlescent Ward")

    assert slots[1].kind == "prescribed_recruit"
    assert slots[1].player_name == "Recruitment Needed"
    assert slots[1].eso_class == "Warden"
    assert slots[1].build_name == "Brittle Warden"
    assert slots[1].gear_summary == "Serpent's Disdain + Pillager's Profit"
    assert slots[1].gear_sets == ("Serpent's Disdain", "Pillager's Profit")
    assert slots[1].role == "Healer"
    assert slots[1].source_kind == "optimizer_prescription"
    assert slots[1].candidate_id == "optimizer:Healer 1"
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


def test_live_prescription_transfer_uses_generated_roster_draft_api() -> None:
    source = Path("ui/team_prescription_roster_transfer_support.py").read_text(encoding="utf-8")

    assert "GeneratedRosterDraftService" in source
    assert "GeneratedRosterDraftSlot" in source
    assert "GeneratedRosterPlanService" not in source
    assert "GeneratedRosterPlanSlot" not in source


def test_optimizer_send_is_owned_by_raid_plan_not_legacy_roster() -> None:
    source = Path("ui/team_prescription_roster_transfer_support.py").read_text(
        encoding="utf-8"
    )

    handler = source.split(
        "def _send_generated_prescription_to_raid_plan", 1
    )[1].split("def install()", 1)[0]

    assert "raid_plan_from_generated_slots" in handler
    assert 'window.pages.get("raid_plans")' in handler
    assert "raid_plans.plan_repository.save(plan)" in handler
    assert "raid_plans.apply_plan(plan)" in handler
    assert 'window.show_page("raid_plans")' in handler
    assert 'window.show_page("roster_page")' not in handler
    assert "base_plan=base_plan" in handler


def test_optimizer_install_overrides_send_handler_with_raid_plan_handoff() -> None:
    source = Path("ui/team_prescription_roster_transfer_support.py").read_text(
        encoding="utf-8"
    )

    assert (
        "MainWindow._send_optimized_team_to_roster = "
        "_send_generated_prescription_to_raid_plan"
    ) in source


def test_optimizer_opened_from_raid_plan_binds_origin_identity() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    block = source.split('if page_name == "console:6":', 1)[1].split(
        'if page_name == "console:2":', 1
    )[0]
    assert 'self.page_containers.get("raid_plans")' in block
    assert "raid_plans.current_plan()" in block
    assert "optimizer._raid_plan_origin_id = origin.plan_id" in block
    assert "optimizer._raid_plan_origin_trial_id = origin.trial_id" in block
