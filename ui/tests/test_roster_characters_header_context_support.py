from pathlib import Path


def test_characters_tab_hides_assignment_header_filters_only():
    source = Path("ui/roster_characters_header_context_support.py").read_text(encoding="utf-8")
    assert '("view_combo", "role_combo", "show_combo")' in source
    assert 'tabs.tabText(index).strip().casefold() == "characters"' in source
    assert 'container.setVisible(not hide)' in source


def test_character_header_context_support_installs_after_roster_composition():
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")
    assert 'install_roster_characters_header_context_support()' in source
    assert source.index('install_roster_team_assignment_filter_support()') < source.index('install_roster_characters_header_context_support()')
