from __future__ import annotations

from pathlib import Path


def test_encounter_board_resolves_qvboxlayout_locally_for_packaged_runtime() -> None:
    source = Path("ui/components/encounter_board.py").read_text(encoding="utf-8")

    function = source.split("def _build_ui(self):", 1)[1].split(
        "def _wire_signals", 1
    )[0]
    assert "from PySide6.QtWidgets import QVBoxLayout as _QVBoxLayout" in function
    assert "root = _QVBoxLayout(self)" in function
