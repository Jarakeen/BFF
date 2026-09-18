from types import SimpleNamespace

from ui.components.foundry_sidebar import CORE_NAV_SECTIONS
from ui.encounters_page import EncountersPage
from ui.main_window import MainWindow


def _section(label: str):
    return next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == label
    )


def test_sidebar_uses_requested_workflow_domain_order():
    labels = [
        item.get("label")
        for item in CORE_NAV_SECTIONS
        if isinstance(item, dict)
    ]
    assert labels == [
        "Raid",
        "Team",
        "Build",
        "Encounter",
        "Review",
        "Achievement",
        "Collectibles",
        "Tools",
        "Settings",
    ]


def test_team_menu_owns_people_and_team_planning_tools():
    section = _section("Team")
    assert section["children"] == [
        ("Roster", "roster_workspace"),
        ("Comp Builder", "comp_builder"),
        ("Optimizer Adviser", "console:6"),
        ("Coverage", "console:7"),
    ]


def test_build_menu_owns_build_workspaces():
    section = _section("Build")
    assert section["children"] == [
        ("Builds", "console:2"),
        ("Rotation Builder", "rotations"),
        ("Extreme Builder", "extreme_optimization"),
    ]


def test_raid_menu_owns_run_specific_planning_workflow():
    section = _section("Raid")
    assert section["children"] == [
        ("Raid Plans", "raid_plans"),
        ("Assignments", "assignments"),
        ("Readiness", "readiness"),
        ("Live Raid", "live_raid"),
    ]


def test_encounter_and_reference_data_remain_separate_destinations():
    encounter = _section("Encounter")
    assert ("Mechanics & Timelines", "console:4") in encounter["children"]
    assert not any(
        page == "tools:reference_data"
        for _label, page in encounter["children"]
    )
    assert ("Reference Data", "tools:reference_data") in _section("Tools")["children"]


def test_review_menu_owns_raid_review_and_top_gear():
    assert _section("Review")["children"] == [
        ("Raid Review", "raid_review"),
        ("Top Gear", "console:3"),
    ]



def test_encounters_boss_index_uses_same_canonical_guide_rows_as_mechanics():
    rows = (
        SimpleNamespace(
            encounter_id="reef_one",
            content_id="dreadsail_reef",
            content_name="Dreadsail Reef",
            name="Boss One",
        ),
        SimpleNamespace(
            encounter_id="reef_two",
            content_id="dreadsail_reef",
            content_name="Dreadsail Reef",
            name="Boss Two",
        ),
        SimpleNamespace(
            encounter_id="sunspire_one",
            content_id="sunspire",
            content_name="Sunspire",
            name="Other Boss",
        ),
    )
    page = SimpleNamespace(
        guide_service=SimpleNamespace(encounter_summaries=lambda: rows),
        expedition=SimpleNamespace(
            expedition=SimpleNamespace(Expedition="Dreadsail Reef", Objective="Boss One")
        ),
    )

    result = EncountersPage._boss_rows_for_active_trial(page)

    assert [row.encounter_id for row in result] == ["reef_one", "reef_two"]


def test_encounters_boss_selection_updates_shared_expedition_objective():
    expedition = SimpleNamespace(Expedition="Dreadsail Reef", Objective="Boss One")
    page = SimpleNamespace(
        _guide_summaries=(
            SimpleNamespace(name="Boss One"),
            SimpleNamespace(name="Boss Two"),
        ),
        expedition=SimpleNamespace(expedition=expedition),
    )

    EncountersPage._boss_changed(page, 1)

    assert expedition.Objective == "Boss Two"


def test_help_guide_is_not_a_global_sidebar_destination():
    assert _section("Settings").get("page") == "settings"
    assert not any(
        (
            isinstance(item, tuple)
            and len(item) >= 2
            and item[1] == "help"
        )
        or (
            isinstance(item, dict)
            and any(page == "help" for _label, page in item.get("children", []))
        )
        for item in CORE_NAV_SECTIONS
    )


def test_optimized_build_identity_preserves_player_character_and_build():
    build = SimpleNamespace(
        Name="Player One",
        CharacterName="Character One",
        BuildName="Trial Build",
    )
    assert MainWindow._build_identity(build) == (
        "Player One",
        "Character One",
        "Trial Build",
    )


def test_roster_bridge_matches_existing_person_without_creating_one():
    roster_page = SimpleNamespace(members=[
        SimpleNamespace(PlayerName="Player One", CharacterName="Character One"),
        SimpleNamespace(PlayerName="Player Two", CharacterName="Character Two"),
    ])

    match = MainWindow._matching_roster_member(
        roster_page,
        {
            "kind": "saved",
            "player": "Player One",
            "character": "Character One",
            "build": "Trial Build",
        },
    )

    assert match is roster_page.members[0]
    assert len(roster_page.members) == 2
