from pathlib import Path

from services.accessibility_preferences import (
    AccessibilityPreferences,
    VISUAL_THEME_FOUNDRY,
    VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    VISUAL_THEME_RYLO,
    VISUAL_THEME_RYLO_CITY,
    is_foundry_visual_theme,
    is_rylo_visual_theme,
)
from ui.theme.theme_manager import ThemeManager


def test_legacy_theme_keys_remain_selectable(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    assert preferences.set_visual_theme(VISUAL_THEME_FOUNDRY) == VISUAL_THEME_FOUNDRY
    assert preferences.visual_theme() == VISUAL_THEME_FOUNDRY

    assert preferences.set_visual_theme(VISUAL_THEME_RYLO) == VISUAL_THEME_RYLO
    assert preferences.visual_theme() == VISUAL_THEME_RYLO


def test_new_theme_keys_are_independent_options(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    assert (
        preferences.set_visual_theme(VISUAL_THEME_FOUNDRY_FIELD_JOURNAL)
        == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL
    )
    assert preferences.visual_theme() == VISUAL_THEME_FOUNDRY_FIELD_JOURNAL

    assert preferences.set_visual_theme(VISUAL_THEME_RYLO_CITY) == VISUAL_THEME_RYLO_CITY
    assert preferences.visual_theme() == VISUAL_THEME_RYLO_CITY


def test_visual_theme_menu_exposes_four_distinct_skins() -> None:
    options = dict(ThemeManager.visual_theme_options())

    assert options[VISUAL_THEME_FOUNDRY] == "Foundry Grimoire"
    assert options[VISUAL_THEME_RYLO] == "Rylo Grayscale"
    assert options[VISUAL_THEME_FOUNDRY_FIELD_JOURNAL] == "Foundry · Field Journal"
    assert options[VISUAL_THEME_RYLO_CITY] == "Rylo · City After Midnight"


def test_theme_family_helpers_include_old_and_new_skins() -> None:
    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY)
    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY_FIELD_JOURNAL)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO_CITY)
