from pathlib import Path


def test_rylo_final_polish_removes_legacy_teal_and_crimson_states() -> None:
    source = Path("ui/rylo_surface_icon_fix.py").read_text(encoding="utf-8")

    assert 'QPushButton[secondary="true"]' in source
    assert 'QPushButton[success="true"]' in source
    assert 'QPushButton[settingsNav="true"]:checked' in source
    assert 'border-left: 4px solid #6FA8D3;' in source
    assert 'background-color: #181A1D;' in source
    assert '#8B1E24' not in source


def test_rylo_raid_engine_uses_dedicated_ring_and_star_assets() -> None:
    source = Path("ui/rylo_surface_icon_fix.py").read_text(encoding="utf-8")

    assert 'rylo_raid_engine_oval.svg' in source
    assert 'rylo_raid_engine_star.svg' in source
    assert Path("assets/decorative/rylo_raid_engine_oval.svg").exists()
    assert Path("assets/decorative/rylo_raid_engine_star.svg").exists()
    assert 'CompositionRingWidget._is_rylo = staticmethod(lambda: False)' in source


def test_rylo_raid_engine_planning_pulse_is_blue_gray_not_teal_green() -> None:
    source = Path("ui/rylo_surface_icon_fix.py").read_text(encoding="utf-8")

    assert 'ReadinessRingWidget.paintEvent = readiness_paint_theme_aware' in source
    assert 'QColor("#6FA8D3")' in source
    assert 'QColor("#30343A")' in source
