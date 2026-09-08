from pathlib import Path


SOURCE = Path("ui/stickerbook_page.py").read_text(encoding="utf-8")


def test_stickerbook_uses_checkbox_grid_without_redundant_missing_list():
    assert "self.missing_box" not in SOURCE
    assert "stickerMissing" not in SOURCE
    assert "Missing {len(missing)} piece(s)" not in SOURCE
    assert "grid.addWidget(checkbox, index // 3, index % 3)" in SOURCE


def test_stickerbook_piece_grid_keeps_three_equal_columns():
    assert "for column in range(3):" in SOURCE
    assert "grid.setColumnStretch(column, 1)" in SOURCE
