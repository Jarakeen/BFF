from pathlib import Path

import ui.roster_assignment_persistence_support as support


def test_assignment_autocomplete_columns_are_wider_than_their_menu_minimum() -> None:
    source = Path(support.__file__).read_text(encoding="utf-8")

    assert "header.setStretchLastSection(False)" in source
    assert "header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)" in source
    assert "4: 260" in source
    assert "5: 260" in source
