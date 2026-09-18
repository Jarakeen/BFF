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
    assert "#82B6D1" in source
    assert "#D28A51" in source
    assert "#C6A85A" in source
    assert "#A89BC8" in source
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


def test_raid_plan_surface_exposes_roles_and_spots_as_user_language() -> None:
    source = Path("ui/city_raid_plan_workspace_page.py").read_text(encoding="utf-8")

    assert '("Roles", None)' in source
    assert 'Manage Roles / Spots' in source
    assert '("Chairs", None)' not in source
    assert 'Manage Chairs' not in source
    assert "assignment_card.hide()" in source
    assert "Duties live in Assignments" in source


def test_assignment_surface_separates_support_jobs_from_utility() -> None:
    source = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    assert '("Spot", "Player", "Buffs / Debuffs", "Gear / Build", "Source")' in source
    assert '("Spot", "Player", "Utility / Mechanic Job")' in source
    assert 'FoundryCard("Buffs / Debuffs", "checklist")' in source
    assert 'FoundryCard("Utility / Mechanics", "warning")' in source
    assert 'FoundryCard("Plan Snapshot", "compass")' in source
    assert 'FoundryCard("Mechanic Coverage", "shield")' not in source
    assert '"Notes"' not in source.split('self.support_table.setHorizontalHeaderLabels', 1)[1].split(')', 1)[0]
    assert 'form.addRow("Notes", self.selected_notes)' in source


def test_roster_top_surface_has_badges_and_mockup_proportion_polish() -> None:
    source = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    for key in ("players", "characters", "teams", "availability", "recruitment", "archive"):
        assert f'"{key}"' in source
    assert "rosterMetricBadge" in source
    assert "setMaximumWidth(390)" in source
    assert "self.table.setMinimumWidth(720)" in source
