from pathlib import Path
from types import SimpleNamespace

from ui.roster_team_assignment_filter_support import (
    CanonicalTeamMembership,
    _member_belongs_to_team,
)


def test_team_cards_filter_assignments_to_selected_team():
    source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")
    assert 'page.assignment_team_filter = team_name' in source
    assert 'page.tabs.setCurrentIndex(index)' in source
    assert '_member_belongs_to_team' in source
    assert 'catalog.assignments_for_team(team_name)' in source


def test_assignment_team_filter_uses_team_selector():
    source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")
    assert 'combo = QComboBox()' in source
    assert 'combo.addItem(_ALL_TEAMS_LABEL, "")' in source
    assert 'page.roster_service.list_team_names()' in source
    assert 'page.assignment_team_filter = team_name' in source
    assert 'Assignments showing all roster members.' in source


def test_team_card_selection_syncs_assignment_selector():
    source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")
    assert '_refresh_team_selector(page)' in source
    assert 'combo.findData(selected)' in source
    assert '_select_team_for_assignments(page, team)' in source


def test_canonical_character_id_wins_over_matching_legacy_names():
    membership = CanonicalTeamMembership(
        player_ids=frozenset({"player-a"}),
        character_ids=frozenset({"character-a"}),
        legacy_names=frozenset({("jarakeen", "magrat")}),
    )
    member = SimpleNamespace(
        Team="",
        CanonicalPlayerId="player-a",
        CanonicalCharacterId="character-b",
        PlayerName="Jarakeen",
        CharacterName="Magrat",
    )

    assert not _member_belongs_to_team(None, member, "Performance Mode", membership)


def test_player_only_roster_row_uses_canonical_player_id():
    membership = CanonicalTeamMembership(
        player_ids=frozenset({"player-a"}),
        character_ids=frozenset({"character-a"}),
        legacy_names=frozenset({("jarakeen", "magrat")}),
    )
    member = SimpleNamespace(
        Team="",
        CanonicalPlayerId="player-a",
        CanonicalCharacterId="",
        PlayerName="Changed Display Name",
        CharacterName="",
    )

    assert _member_belongs_to_team(None, member, "Performance Mode", membership)


def test_legacy_roster_row_keeps_name_fallback_without_canonical_ids():
    membership = CanonicalTeamMembership(
        legacy_names=frozenset({("legacy player", "legacy toon")}),
    )
    member = SimpleNamespace(
        Team="",
        CanonicalPlayerId="",
        CanonicalCharacterId="",
        PlayerName="Legacy Player",
        CharacterName="Legacy Toon",
    )

    assert _member_belongs_to_team(None, member, "Performance Mode", membership)


def test_team_assignment_filter_installs_after_roster_composition():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")
    filter_pos = source.index("install_roster_team_assignment_filter_support()")
    assert source.index("install_roster_player_architecture_support()") < filter_pos
    assert source.index("install_roster_import_support()") < filter_pos
