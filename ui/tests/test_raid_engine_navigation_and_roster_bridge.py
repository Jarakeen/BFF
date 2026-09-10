from types import SimpleNamespace

from ui.components.foundry_sidebar import CORE_NAV_SECTIONS
from ui.encounters_page import EncountersPage
from ui.main_window import MainWindow


def _section(label: str):
    return next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == label
    )


def test_roster_menu_owns_rotation_workflow():
    section = _section("Roster")
    assert section.get("page") == "operations_console"
    assert section["children"] == [
        ("Characters", "characters"),
        ("Builds", "console:2"),
        ("Rotations", "rotations"),
    ]


def test_raid_engine_menu_matches_dashboard_workflow():
    section = _section("Raid Engine")
    assert section.get("page") == "raid_engine_dashboard"
    assert section["children"] == [
        ("Comp Maker", "comp_builder"),
        ("Optimization", "console:6"),
        ("Coverage", "console:7"),
        ("Encounters", "console:1"),
        ("Performance", "console:3"),
        ("Mechanics", "console:4"),
    ]


def test_mechanics_is_not_a_top_level_sidebar_section():
    assert not any(
        isinstance(item, dict) and item.get("label") == "Mechanics"
        for item in CORE_NAV_SECTIONS
    )
    assert not any(
        isinstance(item, dict)
        and any(page == "console:8" for _label, page in item.get("children", []))
        for item in CORE_NAV_SECTIONS
    )
    assert ("Reference Data", "tools:reference_data") in _section("Tool")["children"]


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
    assert ("Settings", "settings") in CORE_NAV_SECTIONS
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
