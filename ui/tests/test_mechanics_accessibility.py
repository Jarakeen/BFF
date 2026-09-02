from pathlib import Path

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    COLOR_VISION_STANDARD,
)
from ui import mechanics_page


def test_accessibility_preferences_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "accessibility.json"
    preferences = AccessibilityPreferences(path)

    assert preferences.color_vision_mode() == COLOR_VISION_STANDARD
    assert preferences.set_color_vision_mode(COLOR_VISION_FRIENDLY) == COLOR_VISION_FRIENDLY
    assert preferences.color_vision_mode() == COLOR_VISION_FRIENDLY


def test_mechanics_page_exposes_non_color_only_status_language() -> None:
    source = Path(mechanics_page.__file__).read_text(encoding="utf-8")

    assert 'self.color_vision_combo.addItem("Standard", COLOR_VISION_STANDARD)' in source
    assert 'self.color_vision_combo.addItem("Colorblind Friendly", COLOR_VISION_FRIENDLY)' in source
    assert '"◇  ✓  SAFE / SUCCESS"' in source
    assert '"⬡  ✕  FAILED / DANGER"' in source
    assert '"○  !  ATTENTION / WARNING"' in source
    assert '"□  —  NOT APPLICABLE"' in source
    assert 'background-color: #101315;' in source
    assert 'self.tabs.addTab(self._mechanics_tab(), "MECHANICS")' in source
