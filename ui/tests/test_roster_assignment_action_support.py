from pathlib import Path


def test_assignment_actions_remove_ready_and_add_requested_buttons():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert '== "ready"' in source
    assert "table.removeColumn(ready_column)" in source
    assert 'QPushButton("Send to Comp Maker")' in source
    assert 'QPushButton("Evaluate")' in source
    assert 'QPushButton("Encounter")' in source
    assert 'QPushButton("Gear Lookup")' in source


def test_assignment_actions_route_to_existing_canonical_pages():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert '_show_page(page, "comp_builder")' in source
    assert '_show_page(page, "console:7")' in source
    assert '_show_page(page, "console:1")' in source
    assert '_show_page(page, "gear_lookup")' in source
    assert "coverage.set_team_scope(team_name, selected, total_slots=len(members))" in source


def test_assignment_actions_install_after_persistence_layer():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_roster_assignment_action_support()" in source
    assert source.index("install_roster_assignment_persistence_support()") < source.index(
        "install_roster_assignment_action_support()"
    )
