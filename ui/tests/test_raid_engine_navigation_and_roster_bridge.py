from types import SimpleNamespace

from ui.components.foundry_sidebar import CORE_NAV_SECTIONS
from ui.main_window import MainWindow


def test_raid_engine_menu_matches_workflow_order():
    section = next(
        item for item in CORE_NAV_SECTIONS
        if isinstance(item, dict) and item.get("label") == "Raid Engine"
    )
    assert section["children"] == [
        ("Overview", "operations_console"),
        ("Builds", "console:2"),
        ("Rotations", "rotations"),
        ("Comp Builder", "comp_builder"),
        ("Roster", "roster_page"),
        ("Optimization", "console:6"),
        ("Coverage", "console:7"),
        ("Encounters", "console:1"),
        ("Performance", "console:3"),
        ("Mechanics", "console:4"),
        ("Reference Data", "console:8"),
        ("Timers", "timers"),
    ]


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
