from pathlib import Path


def test_assignment_actions_hide_ready_and_add_simplified_buttons():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert '== "ready"' in source
    assert "table.setColumnHidden(ready_column, True)" in source
    assert 'QPushButton("Save")' in source
    assert 'QPushButton("Clear")' in source
    assert 'QPushButton("Send to Comp Maker")' in source
    assert 'QPushButton("Evaluate")' in source
    assert 'QPushButton("Encounter")' not in source
    assert 'QPushButton("Gear Lookup")' not in source


def test_assignment_actions_use_requested_two_by_two_order():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert "actions.addWidget(save, 0, 0)" in source
    assert "actions.addWidget(clear, 0, 1)" in source
    assert "actions.addWidget(send, 1, 0)" in source
    assert "actions.addWidget(evaluate, 1, 1)" in source


def test_assignment_actions_keep_flat_card_and_remove_all_header_content():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert "_clear_card_header(card)" in source
    assert 'card.set_title("")' in source
    assert 'card.set_icon("")' in source
    assert 'card.set_badge("")' in source
    assert "_clear_layout(card.header_action_layout)" in source
    assert "card.header.setMaximumHeight(0)" in source
    assert 'card.setProperty("flatActionCard", True)' in source
    assert "_clear_card_body(card)" in source
    assert "button.setMinimumHeight(52)" in source
    assert "QSizePolicy.Policy.Expanding" in source
    assert "actions.setRowStretch(0, 1)" in source
    assert "actions.setRowStretch(1, 1)" in source


def test_team_summary_uses_plain_body_heading_not_button_like_header_strip():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert "_flatten_team_summary_header(self)" in source
    assert 'title = QLabel("Team Summary")' in source
    assert 'title.setProperty("cardTitle", True)' in source
    assert "card.body_layout.insertWidget(0, title)" in source
    assert "card.header.setMaximumHeight(0)" in source


def test_assignment_actions_do_not_show_hover_panels_over_the_table():
    action_source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")
    persistence_source = Path("ui/roster_assignment_persistence_support.py").read_text(encoding="utf-8")
    encounter_source = Path("ui/roster_encounter_assignment_context_support.py").read_text(encoding="utf-8")
    team_source = Path("ui/roster_team_assignment_filter_support.py").read_text(encoding="utf-8")

    assert 'button.setToolTip("")' in action_source
    assert '_field_tooltip' not in persistence_source
    assert 'combo.setToolTip("")' in persistence_source
    assert 'combo.setToolTip("")' in encounter_source
    assert 'combo.setToolTip("")' in team_source


def test_save_and_clear_use_selected_team_and_optional_boss_context():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert "selected_encounter_id(page)" in source
    assert "service.set_field(" in source
    assert "service.clear_context(" in source
    assert "page._populate_assignment_table()" in source
    assert "now inherits" in source


def test_assignment_actions_route_only_to_comp_maker_and_coverage():
    source = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert '_show_page(page, "comp_builder")' in source
    assert '_show_page(page, "console:7")' in source
    assert '_show_page(page, "console:1")' not in source
    assert '_show_page(page, "gear_lookup")' not in source
    assert "coverage.set_team_scope(team_name, selected, total_slots=len(members))" in source


def test_assignment_actions_install_after_persistence_layer():
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "install_roster_assignment_action_support()" in source
    assert source.index("install_roster_assignment_persistence_support()") < source.index(
        "install_roster_assignment_action_support()"
    )
