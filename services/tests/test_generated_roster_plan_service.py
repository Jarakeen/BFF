from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)


def _service(tmp_path):
    return GeneratedRosterPlanService(EsoDatabase(tmp_path / "eso.db"))


def test_generated_roster_plan_persists_saved_and_recruit_slots(tmp_path) -> None:
    service = _service(tmp_path)
    slots = (
        GeneratedRosterPlanSlot(
            slot_name="Main Tank",
            kind="saved",
            player_name="Tank Player",
            character_name="Bone Tank",
            eso_class="Necromancer",
            build_name="YOUR TANK BUILD",
            gear_summary="Turning Tide + Pearlescent Ward",
        ),
        GeneratedRosterPlanSlot(
            slot_name="Healer 1",
            kind="prescribed_recruit",
            player_name="Recruitment Needed",
            character_name="",
            eso_class="Warden",
            build_name="Brittle Warden",
            gear_summary="Serpent's Disdain + Pillager's Profit",
            unresolved="traits unresolved",
        ),
        GeneratedRosterPlanSlot(
            slot_name="DD 1",
            kind="open_recruit",
            player_name="Recruitment Needed",
            character_name="",
            eso_class="Any class",
            build_name="Open requirement",
            unresolved="class/build evidence unresolved",
        ),
    )

    saved = service.save_plan(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        difficulty="Veteran Hardmode",
        slots=slots,
    )
    loaded = service.load_plan("godslayer prescribed roster")

    assert loaded is not None
    assert loaded.plan_id == saved.plan_id
    assert loaded.goal == "Godslayer"
    assert loaded.difficulty == "Veteran Hardmode"
    assert loaded.slots == slots
    assert service.list_plan_names() == ("Godslayer Prescribed Roster",)
    assert service.latest_plan() == loaded


def test_resending_same_named_plan_replaces_slots_instead_of_duplicating(tmp_path) -> None:
    service = _service(tmp_path)
    service.save_plan(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        difficulty="Veteran",
        slots=(
            GeneratedRosterPlanSlot(
                slot_name="Main Tank",
                kind="open_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Any class",
                build_name="Open requirement",
            ),
        ),
    )

    replacement = (
        GeneratedRosterPlanSlot(
            slot_name="Main Tank",
            kind="saved",
            player_name="Tank Player",
            character_name="Bone Tank",
            eso_class="Necromancer",
            build_name="Tank Build",
        ),
        GeneratedRosterPlanSlot(
            slot_name="Healer 1",
            kind="prescribed_recruit",
            player_name="Recruitment Needed",
            character_name="",
            eso_class="Warden",
            build_name="Support Healer",
        ),
    )
    service.save_plan(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        difficulty="Veteran Hardmode",
        slots=replacement,
    )

    loaded = service.load_plan("Godslayer Prescribed Roster")
    assert loaded is not None
    assert loaded.difficulty == "Veteran Hardmode"
    assert loaded.slots == replacement
    assert service.list_plan_names() == ("Godslayer Prescribed Roster",)
