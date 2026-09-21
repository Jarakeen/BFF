from __future__ import annotations

from pathlib import Path


def test_raid_map_accessibility_resolves_layout_locally_for_packaged_runtime() -> None:
    source = Path("ui/encounter_board_accessibility.py").read_text(encoding="utf-8")

    function = source.split("def raid_map_tab(self) -> QWidget:", 1)[1].split(
        "def build_ui_with_raid_map", 1
    )[0]
    assert "from PySide6.QtWidgets import QVBoxLayout as _QVBoxLayout" in function
    assert "root = _QVBoxLayout(tab)" in function
