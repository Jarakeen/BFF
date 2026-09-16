from pathlib import Path

from services.accessibility_preferences import (
    AccessibilityPreferences,
    COLOR_VISION_FRIENDLY,
    VISUAL_THEME_RYLO_CITY,
)
from ui.theme.theme_manager import ThemeManager


def test_urban_wilderness_is_the_only_selectable_visual_profile(tmp_path: Path) -> None:
    preferences = AccessibilityPreferences(tmp_path / "accessibility.json")

    assert ThemeManager.visual_theme_options() == (
        (VISUAL_THEME_RYLO_CITY, "Urban Wilderness"),
    )
    assert ThemeManager.color_vision_options() == (
        (COLOR_VISION_FRIENDLY, "Colorblind Friendly"),
    )

    for legacy in (
        "foundry_grimoire",
        "rylo_grayscale",
        "foundry_field_journal",
        "anything_else",
    ):
        assert preferences.set_visual_theme(legacy) == VISUAL_THEME_RYLO_CITY
        assert preferences.visual_theme() == VISUAL_THEME_RYLO_CITY


def test_complete_raid_workspace_is_registered_as_first_class_pages() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    for page_type, route in (
        ("CityRaidRosterWorkspacePage()", "roster_workspace"),
        ("CityRaidPlanWorkspacePage()", "raid_plans"),
        ("CityRaidAssignmentsPage()", "assignments"),
        ("CityRaidReadinessPage()", "readiness"),
        ("CityLiveRaidPage()", "live_raid"),
    ):
        assert page_type in source
        assert f'_register_page(window, "{route}"' in source

    assert 'window.pages["assignments"] = page' not in source
    assert 'MainWindow.' not in source


def test_raid_lead_navigation_uses_real_current_routes() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    for label, route in (
        ("Roster", "roster_workspace"),
        ("Raid Plans", "raid_plans"),
        ("Assignments", "assignments"),
        ("Readiness", "readiness"),
        ("Live Raid", "live_raid"),
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


def test_roster_workspace_exposes_six_card_workspaces_and_urban_wilderness_art() -> None:
    base = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")
    dashboard = Path("ui/themed_raid_roster_workspace_page.py").read_text(encoding="utf-8")
    wrapper = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    for title in (
        "PLAYERS",
        "CHARACTERS",
        "TEAMS",
        "AVAILABILITY",
        "RECRUITMENT",
        "ARCHIVE",
    ):
        assert f'"{title}"' in base

    assert "QTabWidget" not in dashboard
    assert "self.tabs" not in dashboard
    assert '"city_night"' in dashboard
    assert '"roster_people.webp"' in dashboard
    assert '"roster_team.webp"' in dashboard
    assert "class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):" in wrapper
    assert "self.tabs" not in wrapper

    # Final composition polish protects the approved mockup proportions.
    assert '"players": "users"' in wrapper
    assert '"characters": "character"' in wrapper
    assert 'setProperty("rosterMetricBadge", True)' in wrapper
    assert "setMaximumWidth(390)" in wrapper
    assert "setMaximumHeight(220)" in wrapper
    assert "self.table.setMinimumWidth(720)" in wrapper


def test_city_key_remains_the_compatibility_storage_key_for_urban_wilderness() -> None:
    source = Path("services/accessibility_preferences.py").read_text(encoding="utf-8")

    assert 'VISUAL_THEME_RYLO_CITY = "rylo_city_night"' in source
    assert "VISUAL_THEME_URBAN_WILDERNESS = VISUAL_THEME_RYLO_CITY" in source
