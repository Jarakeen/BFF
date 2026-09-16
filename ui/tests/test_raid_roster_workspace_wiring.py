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


def test_new_themes_are_additive_and_legacy_theme_keys_remain_valid(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    expected = {
        VISUAL_THEME_FOUNDRY,
        VISUAL_THEME_RYLO,
        VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
        VISUAL_THEME_RYLO_CITY,
    }
    assert {key for key, _label in ThemeManager.visual_theme_options()} == expected

    for theme in expected:
        assert preferences.set_visual_theme(theme) == theme
        assert preferences.visual_theme() == theme

    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY)
    assert is_foundry_visual_theme(VISUAL_THEME_FOUNDRY_FIELD_JOURNAL)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO)
    assert is_rylo_visual_theme(VISUAL_THEME_RYLO_CITY)


def test_new_roster_workspace_is_registered_beside_legacy_assignment_surface() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    assert 'ThemedRaidRosterWorkspacePage()' in source
    assert '_register_page(window, "roster_workspace", roster_workspace)' in source
    assert 'page = window.pages.get("roster_page")' in source
    assert 'window.pages["assignments"] = page' in source
    assert 'window.page_containers["assignments"] = container' in source
    assert 'MainWindow.' not in source


def test_raid_lead_navigation_uses_real_current_routes() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    for label, route in (
        ("Roster", "roster_workspace"),
        ("Raid Plans", "raid_plans"),
        ("Assignments", "assignments"),
        ("Builds", "console:2"),
        ("Rotation Builder", "rotations"),
        ("Extreme Builder", "extreme_optimization"),
        ("Encounters", "console:1"),
        ("Mechanics & Timelines", "console:4"),
        ("Coverage", "console:7"),
        ("Comp Maker", "comp_builder"),
        ("Optimizer Adviser", "console:6"),
    ):
        assert f'("{label}", "{route}")' in source


def test_roster_workspace_exposes_requested_tabs_and_theme_assets() -> None:
    source = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")
    wrapper = Path("ui/themed_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    for title in (
        "PLAYERS",
        "CHARACTERS",
        "TEAMS",
        "AVAILABILITY",
        "RECRUITMENT",
        "ARCHIVE",
    ):
        assert f'"{title}"' in source

    assert '"roster_rylo_sketch.svg"' in wrapper
    assert '"roster_foundry_sketch.svg"' in wrapper
    assert "is_rylo_visual_theme" in wrapper
    assert "refresh_theme_assets" in wrapper


def test_city_theme_inherits_rylo_icon_and_header_language_without_replacing_legacy_rylo() -> None:
    icons = Path("ui/ux_icons.py").read_text(encoding="utf-8")
    header = Path("ui/components/foundry_header.py").read_text(encoding="utf-8")
    cards = Path("ui/components/foundry_card.py").read_text(encoding="utf-8")

    assert "is_rylo_visual_theme" in icons
    assert "is_rylo_visual_theme" in header
    assert "is_rylo_visual_theme" in cards
    assert 'VISUAL_THEME_RYLO = "rylo_grayscale"' in Path(
        "services/accessibility_preferences.py"
    ).read_text(encoding="utf-8")
    assert 'VISUAL_THEME_RYLO_CITY = "rylo_city_night"' in Path(
        "services/accessibility_preferences.py"
    ).read_text(encoding="utf-8")
