from pathlib import Path


def test_roster_workspace_uses_raid_lead_top_level_tabs():
    source = Path("ui/roster_workspace_ux_support.py").read_text(encoding="utf-8")
    assert 'tabs.addTab(personnel, "ROSTER")' in source
    assert 'tabs.addTab(teams_workspace, "TEAMS")' in source
    assert 'tabs.addTab(assignments, "ASSIGNMENTS")' in source
    assert 'tabs.addTab(characters, "PEOPLE & BUILDS")' in source
    assert 'tabs.setCurrentWidget(personnel)' in source


def test_roster_workspace_merges_team_schedule_into_teams():
    source = Path("ui/roster_workspace_ux_support.py").read_text(encoding="utf-8")
    assert 'sub_tabs.addTab(teams_tab, "OVERVIEW")' in source
    assert 'sub_tabs.addTab(schedule_tab, "SCHEDULE & MANAGEMENT")' in source
    assert 'page.team_workspace_tabs = sub_tabs' in source


def test_roster_workspace_exposes_obvious_creation_actions():
    source = Path("ui/roster_workspace_ux_support.py").read_text(encoding="utf-8")
    assert 'QPushButton("Add Player")' in source
    assert 'QPushButton("Import Roster")' in source
    assert 'QPushButton("Open Comp Maker")' in source
    assert '_import_roster_from_file(page)' in source
    assert 'show_page("comp_builder")' in source


def test_roster_workspace_is_installed_after_existing_roster_composition():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")
    assert 'install_roster_workspace_ux_support()' in source
    assert source.index('install_roster_import_support()') < source.index('install_roster_workspace_ux_support()')
    assert source.index('install_user_workspace_polish_support()') < source.index('install_roster_workspace_ux_support()')
