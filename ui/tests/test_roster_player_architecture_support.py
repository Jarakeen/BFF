from pathlib import Path

from ui import roster_player_architecture_support


def test_roster_workspace_exposes_character_tree_and_team_cards() -> None:
    source = Path(roster_player_architecture_support.__file__).read_text(encoding="utf-8")

    assert 'self.tabs.insertTab(1, characters_tab, "CHARACTERS")' in source
    assert 'self.tabs.insertTab(2, personnel_tab, "PERSONNEL")' in source
    assert 'self.tabs.insertTab(3, teams_tab, "TEAMS")' in source
    assert 'FoundryCard("Players, Characters & Builds"' in source
    assert "QTreeWidget" in source
    assert 'player_item.setData(0, _KIND_ROLE, "player")' in source
    assert 'character_item.setData(0, _KIND_ROLE, "character")' in source
    assert 'build_item.setData(0, _KIND_ROLE, "build")' in source


def test_team_cards_use_explicit_focus_and_canonical_assignments() -> None:
    source = Path(roster_player_architecture_support.__file__).read_text(encoding="utf-8")

    assert 'focus_label = QLabel(schedule.CurrentFocus or "Current focus not set")' in source
    assert "catalog_service.assignments_for_team(schedule.TeamName)" in source
    assert 'f"Build assignments: {len(assignments)}\\n"' in source
    assert "Current Focus is entered on Team Schedule" in source


def test_character_tree_reads_canonical_player_character_build_ownership() -> None:
    source = Path(roster_player_architecture_support.__file__).read_text(encoding="utf-8")

    assert 'catalog.get("players", [])' in source
    assert 'catalog.get("characters", [])' in source
    assert 'catalog.get("builds", [])' in source
    assert 'catalog.get("team_assignments", [])' in source
    assert "characters_for_player" in source
    assert "builds_for_character" in source
    assert "assignments_for_build" in source
