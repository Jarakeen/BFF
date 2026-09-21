from pathlib import Path


def test_urban_wilderness_raid_map_restores_phase135_arena_background() -> None:
    source = Path("ui/urban_wilderness_accessibility_polish.py").read_text(
        encoding="utf-8"
    )

    assert "QPolygonF" in source
    assert "def accessible_draw_arena(self) -> None:" in source
    assert 'shell = QColor("#081315")' in source
    assert 'stone_dark = QColor("#0D1B1D")' in source
    assert 'stone_mid = QColor("#122326")' in source
    assert 'stone_light = QColor("#183136")' in source
    assert 'brass = QColor("#716346")' in source
    assert 'title = self.scene.addText("ENCOUNTER ARENA")' in source
    assert "self.scene.addPolygon(" in source
    assert "self.scene.addEllipse(" in source
    assert "board.EncounterBoard._draw_arena = accessible_draw_arena" in source


def test_urban_wilderness_color_mode_keeps_original_phase135_background_tone() -> None:
    source = Path("ui/urban_wilderness_accessibility_polish.py").read_text(
        encoding="utf-8"
    )

    assert 'self.view.setBackgroundBrush(QColor("#081315"))' in source
    assert 'self.view.setBackgroundBrush(QColor("#081416"))' not in source
