from pathlib import Path


def test_assignment_action_uses_player_facing_language() -> None:
    source = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")

    assert 'apply_chair.setText("Assign Build to This Player")' in source
    assert 'setProperty("compAssignBuild", True)' in source
    assert 'generate.setText("Fill from Roster")' in source


def test_main_controls_hide_redundant_update_and_optional_strategy_action() -> None:
    source = Path("ui/comp_builder_main_controls_support.py").read_text(encoding="utf-8")

    assert 'update_combo = getattr(page, "update_combo", None)' in source
    assert "host.hide()" in source
    assert 'button = getattr(page, "comp_interesting_strategy_button", None)' in source
    assert "button.hide()" in source


def test_assignment_cue_links_selected_build_to_selected_player_chair() -> None:
    source = Path("ui/comp_builder_assignment_cue_support.py").read_text(encoding="utf-8")

    assert 'page.matrix_table.setProperty("compAssignmentTarget", True)' in source
    assert 'candidate_label.setProperty("compAssignmentSource", True)' in source
    assert 'details.setProperty("compAssignmentSourceCard", True)' in source
    assert 'cue.setProperty("compAssignmentCue", True)' in source
    assert 'picker_support._selected_candidate(page)' in source
    assert 'f"SELECTED BUILD: {candidate_name}\\n"' in source
    assert 'f"TARGET PLAYER / CHAIR: {slot_name} • {role} • {selected_class}"' in source


def test_assignment_layout_gives_space_back_to_both_main_cards() -> None:
    layout = Path("ui/comp_builder_layout_support.py").read_text(encoding="utf-8")

    assert 'assignment_arrow = QLabel("←\\nASSIGN")' not in layout
    assert 'setProperty("compAssignmentArrow", True)' not in layout
    assert "columns.addLayout(left, 1)" in layout
    assert "columns.addLayout(right, 1)" in layout
    assert "columns.setStretch(0, 1)" in layout
    assert "columns.setStretch(1, 1)" in layout


def test_rylo_uses_one_gold_assignment_accent_for_source_and_target() -> None:
    rylo = Path("ui/comp_builder_rylo_support.py").read_text(encoding="utf-8")

    assert 'QTableWidget[compMakerOverview="true"][compAssignmentTarget="true"]::item:selected' in rylo
    assert 'QLabel[compAssignmentSource="true"]' in rylo
    assert 'QLabel[compAssignmentCue="true"]' in rylo
    assert 'QComboBox[compCandidateChoice="true"]' in rylo
    assert 'QPushButton[compAssignBuild="true"]' in rylo
    assert "#B88A3C" in rylo


def test_assignment_cue_installs_after_candidate_picker_and_main_control_surfaces() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    picker = installer.index("install_comp_builder_candidate_picker()")
    main_controls = installer.index("install_comp_builder_main_controls()")
    assignment = installer.index("install_comp_builder_assignment_cue()")
    rylo = installer.index("install_comp_builder_rylo()")
    layout = installer.index("install_comp_builder_layout()")

    assert picker < main_controls < assignment < rylo < layout
