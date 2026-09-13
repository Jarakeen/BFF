from pathlib import Path


def test_team_cards_filter_assignments_to_selected_team():
    source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")
    assert 'page.assignment_team_filter = team_name' in source
    assert 'page.tabs.setCurrentIndex(index)' in source
    assert '_member_belongs_to_team' in source
    assert 'catalog.assignments_for_team(team_name)' in source


def test_assignment_team_filter_can_be_cleared():
    source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")
    assert 'QPushButton("All Teams")' in source
    assert 'page.assignment_team_filter = ""' in source
    assert 'Assignments showing all roster members.' in source


def test_team_assignment_filter_installs_after_roster_composition():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    assert 'install_roster_team_assignment_filter_support()' in source
    assert source.index('install_user_workspace_polish_support()') < source.index('install_roster_team_assignment_filter_support()')
