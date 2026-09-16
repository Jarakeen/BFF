from pathlib import Path

from services.accessibility_preferences import (
    COLOR_VISION_FRIENDLY,
    VISUAL_THEME_URBAN_WILDERNESS,
)
from ui.theme.theme_manager import ThemeManager


def test_urban_wilderness_is_the_only_visible_theme_and_color_profile() -> None:
    assert ThemeManager.visual_theme_options() == (
        (VISUAL_THEME_URBAN_WILDERNESS, "Urban Wilderness"),
    )
    assert ThemeManager.color_vision_options() == (
        (COLOR_VISION_FRIENDLY, "Colorblind Friendly"),
    )


def test_urban_wilderness_palette_avoids_red_green_state_semantics() -> None:
    source = Path("ui/theme/theme_manager.py").read_text(encoding="utf-8")

    assert "URBAN_WILDERNESS_OVERRIDES" in source
    assert "#82B6D1" in source  # confirmed/safe blue
    assert "#D28A51" in source  # blocked/critical orange
    assert "#C6A85A" in source  # partial/warning gold
    assert "#A89BC8" in source  # review lavender
    assert 'app.setProperty("reducedMotion", True)' in source
    assert "animated gradients" in source


def test_raid_sidebar_exposes_the_complete_top_workflow() -> None:
    source = Path("ui/raid_engine_dashboard_support.py").read_text(encoding="utf-8")

    for route in (
        '("Roster", "roster_workspace")',
        '("Raid Plans", "raid_plans")',
        '("Assignments", "assignments")',
        '("Readiness", "readiness")',
        '("Live Raid", "live_raid")',
    ):
        assert route in source


def test_raid_plan_surface_uses_roles_not_chairs() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert '("Roles", None)' in source
    assert 'Manage Roles / Spots' in source
    assert '"Chairs"' not in source


def test_roster_top_surface_has_six_collectibles_style_workspaces_without_visible_tabs() -> None:
    source = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert "self.tabs.tabBar().hide()" in source
    for key in ("players", "characters", "teams", "availability", "recruitment", "archive"):
        assert f'"{key}"' in source
    assert 'prefer="city"' in source
    assert 'prefer="field"' in source
