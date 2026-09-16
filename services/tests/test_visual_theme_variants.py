from pathlib import Path

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    VISUAL_THEME_FOUNDRY,
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO,
    VISUAL_THEME_RYLO_CITY,
    VISUAL_THEME_URBAN_WILDERNESS,
    is_foundry_visual_theme,
    is_rylo_visual_theme,
)
from ui.theme.theme_manager import ThemeManager


def test_all_saved_theme_requests_normalize_to_urban_wilderness(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    for requested in (
        VISUAL_THEME_FOUNDRY,
        VISUAL_THEME_RYLO,
        VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
        VISUAL_THEME_RYLO_CITY,
        "anything-else",
    ):
        assert preferences.set_visual_theme(requested) == VISUAL_THEME_URBAN_WILDERNESS
        assert preferences.visual_theme() == VISUAL_THEME_URBAN_WILDERNESS


def test_visual_theme_menu_exposes_only_urban_wilderness() -> None:
    assert ThemeManager.visual_theme_options() == (
        (VISUAL_THEME_URBAN_WILDERNESS, "Urban Wilderness"),
    )


def test_color_vision_profile_is_locked_to_safe_semantics(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    assert preferences.color_vision_mode() == COLOR_VISION_FRIENDLY
    assert preferences.set_color_vision_mode("standard") == COLOR_VISION_FRIENDLY
    assert ThemeManager.color_vision_options() == (
        (COLOR_VISION_FRIENDLY, "Colorblind Friendly"),
    )


def test_theme_family_helpers_remain_backward_compatible() -> None:
    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY)
    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY_FIELD_JOURNAL)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO_CITY)
