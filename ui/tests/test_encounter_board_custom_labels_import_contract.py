from __future__ import annotations

from pathlib import Path


def test_custom_label_panel_imports_qvboxlayout_before_use() -> None:
    source = Path("ui/encounter_board_custom_labels_support.py").read_text(
        encoding="utf-8"
    )

    import_block = source.split("_INSTALLED = False", 1)[0]
    panel = source.split("def _label_and_key_panel", 1)[1].split(
        "def install()", 1
    )[0]

    assert "QVBoxLayout" in import_block
    assert "stack = QVBoxLayout(panel)" in panel
