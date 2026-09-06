from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.roster_service import RosterService


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
    assert RosterService(service.db).list_team_names() == ["Godslayer Prescribed Roster"]


def test_generated_plan_round_trips_structured_candidate_evidence(tmp_path) -> None:
    service = _service(tmp_path)
    slot = GeneratedRosterPlanSlot(
        slot_name="Off Tank",
        kind="prescribed_recruit",
        player_name="Recruitment Needed",
        character_name="",
        eso_class="Dragonknight",
        build_name="Dragonknight Tank • Oaxiltso",
        gear_summary="Jorvuld's Guidance + Nazaray + Perfected Saxhleel Champion",
        unresolved="Observed snapshot remains partial.",
        role="Tank",
        source_kind="esologs_snapshot",
        source_name="ESO Logs",
        source_url="https://www.esologs.com/reports/example",
        candidate_id="esologs:report:fight:player:tank:dragonknight",
        gear_sets=(
            "Jorvuld's Guidance",
            "Nazaray",
            "Perfected Saxhleel Champion",
        ),
        skills=("Blockade of Frost", "Crushing Shock", "Echoing Vigor"),
        mundus="The Atronach",
    )

    service.save_plan(
        name="RG Prog",
        goal="Rockgrove",
        difficulty="Veteran Hardmode",
        slots=(slot,),
    )

    loaded = service.load_plan("RG Prog")
    assert loaded is not None
    assert loaded.slots == (slot,)
    assert loaded.slots[0].skills == (
        "Blockade of Frost",
        "Crushing Shock",
        "Echoing Vigor",
    )
    assert loaded.slots[0].gear_sets[1] == "Nazaray"
    assert loaded.slots[0].source_kind == "esologs_snapshot"
    assert loaded.slots[0].mundus == "The Atronach"


def test_generated_plan_team_identity_does_not_fabricate_roster_members(tmp_path) -> None:
    service = _service(tmp_path)
    service.save_plan(
        name="GH Prog",
        goal="Gryphon Heart",
        difficulty="Veteran Hardmode",
        slots=(
            GeneratedRosterPlanSlot(
                slot_name="Healer 1",
                kind="prescribed_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Warden",
                build_name="Brittle Warden",
            ),
        ),
    )

    roster = RosterService(service.db)
    assert roster.list_team_names() == ["GH Prog"]
    assert roster.list_members() == []


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
    assert RosterService(service.db).list_team_names() == ["Godslayer Prescribed Roster"]
