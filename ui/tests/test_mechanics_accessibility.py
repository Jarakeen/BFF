from pathlib import Path

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    COLOR_VISION_STANDARD,
)
from ui import encounter_board_accessibility, mechanics_page


def test_accessibility_preferences_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "accessibility.json"
    preferences = AccessibilityPreferences(path)

    assert preferences.color_vision_mode() == COLOR_VISION_STANDARD
    assert preferences.set_color_vision_mode(COLOR_VISION_FRIENDLY) == COLOR_VISION_FRIENDLY
    assert preferences.color_vision_mode() == COLOR_VISION_FRIENDLY


def test_standalone_mechanics_page_has_no_color_vision_controls() -> None:
    source = Path(mechanics_page.__file__).read_text(encoding="utf-8")

    assert "color_vision_combo" not in source
    assert "_apply_color_vision_mode" not in source
    assert 'title="Boss Guide"' in source


def test_encounter_mapping_board_exposes_colorblind_safe_mode() -> None:
    source = Path(encounter_board_accessibility.__file__).read_text(encoding="utf-8")

    assert 'self.color_vision_combo.addItem("Standard", COLOR_VISION_STANDARD)' in source
    assert 'self.color_vision_combo.addItem("Colorblind Friendly", COLOR_VISION_FRIENDLY)' in source
    assert '"Danger": "#D96C1E"' in source
    assert '"Safe": "#347DB3"' in source
    assert '"Stack": "#8066A6"' in source
    assert '"Neutral": "#777B7E"' in source
    assert '"Danger": Qt.PenStyle.SolidLine' in source
    assert '"Safe": Qt.PenStyle.DashLine' in source
    assert '"Stack": Qt.PenStyle.DotLine' in source
    assert '"Neutral": Qt.PenStyle.DashDotLine' in source
    assert "Danger: orange / solid" in source
    assert "Safe: blue / dashed" in source
