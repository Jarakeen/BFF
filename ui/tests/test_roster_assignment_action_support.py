from pathlib import Path


def test_assignment_actions_hide_ready_and_add_requested_buttons():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert '== "ready"' in source
    assert "table.setColumnHidden(ready_column, True)" in source
    assert 'QPushButton("Send to Comp Maker")' in source
    assert 'QPushButton("Evaluate")' in source
    assert 'QPushButton("Encounter")' in source
    assert 'QPushButton("Gear Lookup")' in source


def test_assignment_actions_keep_flat_card_and_remove_all_header_content():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert "_clear_card_header(card)" in source
    assert 'card.set_title("")' in source
    assert 'card.set_icon("")' in source
    assert "card.header_action_layout.takeAt(0)" in source
    assert "card.header.setMaximumHeight(0)" in source
    assert 'card.setProperty("flatActionCard", True)' in source
    assert "_clear_card_body(card)" in source
    assert "button.setMinimumHeight(52)" in source
    assert "QSizePolicy.Policy.Expanding" in source
    assert "actions.setRowStretch(0, 1)" in source
    assert "actions.setRowStretch(1, 1)" in source


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
