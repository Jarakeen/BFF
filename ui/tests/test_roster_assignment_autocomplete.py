from pathlib import Path


def test_assignment_columns_use_contains_autocomplete_and_canonical_coverage_choices() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    assert "QCompleter" in source
    assert "Qt.MatchFlag.MatchContains" in source
    assert "QCompleter.CompletionMode.PopupCompletion" in source
    assert "QComboBox.InsertPolicy.NoInsert" in source
    assert "Type to find assignment" in source
    assert "DEFAULT_RAID_COVERAGE_PROFILE.requirements" in source
    assert 'f"requirement:{requirement.requirement_id}"' in source


def test_primary_and_secondary_assignment_cells_keep_export_backing_items() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    assert "if col in {4, 5}:" in source
    assert "self._set_assignment_cell(row, col, str(value))" in source
    assert "combo.currentTextChanged.connect(item.setText)" in source
    assert "self.assignment_table.setCellWidget(row, column, combo)" in source
