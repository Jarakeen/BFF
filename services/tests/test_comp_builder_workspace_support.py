from pathlib import Path


def test_comp_maker_workspace_hides_verbose_matrix_columns_and_blocks_horizontal_scroll():
    source = Path("ui/comp_builder_workspace_support.py").read_text(encoding="utf-8")

    assert "for column in range(3, 8):" in source
    assert "table.setColumnHidden(column, True)" in source
    assert "ScrollBarAlwaysOff" in source
    assert "SUMMARY_CANDIDATE_COLUMN = 8" in source
    assert "SUMMARY_CONSTRAINT_COLUMN = 9" in source
    assert "SUMMARY_JOB_COLUMN = 10" in source


def test_comp_maker_workspace_keeps_legacy_columns_as_authoritative_storage():
    source = Path("ui/comp_builder_workspace_support.py").read_text(encoding="utf-8")

    assert "_copy_detail_value_to_hidden(page, 4, text)" in source
    assert "_copy_detail_value_to_hidden(page, 5, text)" in source
    assert "_copy_detail_value_to_hidden(page, 6, text)" in source
    assert "_copy_detail_value_to_hidden(page, 7, text)" in source
    assert "_comp_required_gear_sets_by_slot" in source


def test_comp_maker_layout_is_vertical_not_two_column():
    source = Path("ui/comp_builder_layout_support.py").read_text(encoding="utf-8")

    assert "QHBoxLayout" not in source
    assert "root.addWidget(actions, 0)" in source
    assert "root.addWidget(matrix, 0)" in source
    assert "root.addWidget(coverage, 0)" in source
    assert "root.addWidget(details, 0)" in source
    assert "root.addWidget(evidence, 0)" in source
    assert "vertical" in source.casefold()


def test_comp_maker_selected_chair_editor_contains_duties_providers_mechanics_and_build_around():
    source = Path("ui/comp_builder_workspace_support.py").read_text(encoding="utf-8")

    assert '"REQUIRED RESPONSIBILITIES"' in source
    assert '"OPTIONAL / FLEX"' in source
    assert '"PROVIDER OBLIGATIONS"' in source
    assert '"MECHANIC JOBS"' in source
    assert "comp_required_gear_sets_input" in source
    assert 'details.title_label.setText("Selected Chair Setup & Evidence")' in source


def test_comp_maker_rylo_has_explicit_workspace_overrides():
    source = Path("ui/comp_builder_rylo_support.py").read_text(encoding="utf-8")
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    assert "VISUAL_THEME_RYLO" in source
    assert 'QTableWidget[compMakerOverview="true"]' in source
    assert 'QLabel[compMakerChairTitle="true"]' in source
    assert 'QLineEdit[compMakerConstraintInput="true"]' in source
    assert "install_comp_builder_rylo()" in installer
    assert "install_comp_builder_workspace()" in installer
