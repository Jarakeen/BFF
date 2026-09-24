from pathlib import Path


def test_assignments_right_hand_detail_shows_selected_class() -> None:
    source = Path("ui/roster_page.py").read_text(encoding="utf-8")

    assert 'self.assignment_detail_label = QLabel("Class: —")' in source
    assert "self.assignment_table.itemSelectionChanged.connect(self._refresh_assignment_detail)" in source
    assert "class_item = self.assignment_table.item(row, 2)" in source
    assert 'self.assignment_detail_label.setText(f"Class: {eso_class}")' in source
