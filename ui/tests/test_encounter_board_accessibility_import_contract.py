from __future__ import annotations

from pathlib import Path


def test_raid_map_accessibility_imports_qvboxlayout_before_use() -> None:
    source = Path("ui/encounter_board_accessibility.py").read_text(encoding="utf-8")

    import_block = source.split(
        "from services.accessibility_preferences import",
        1,
    )[0]
    assert "QVBoxLayout" in import_block
    assert "root = QVBoxLayout(tab)" in source
    assert import_block.index("QVBoxLayout") < source.index("root = QVBoxLayout(tab)")
