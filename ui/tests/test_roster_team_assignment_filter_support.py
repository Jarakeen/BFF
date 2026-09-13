from pathlib import Path


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


def test_team_assignment_filter_installs_after_roster_composition():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    assert 'install_roster_team_assignment_filter_support()' in source
    assert source.index('install_user_workspace_polish_support()') < source.index('install_roster_team_assignment_filter_support()')
