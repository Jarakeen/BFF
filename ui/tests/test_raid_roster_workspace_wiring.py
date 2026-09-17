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


def test_roster_workspace_keeps_six_cards_without_legacy_filler_art() -> None:
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
    assert "class CityRaidRosterWorkspacePage(ThemedRaidRosterWorkspacePage):" in wrapper
    assert "self.tabs" not in wrapper

    assert "_remove_legacy_city_art" in wrapper
    assert 'for attribute in ("quote_art", "team_art")' in wrapper
    assert "decorative assets never determine page/card geometry" in wrapper

    assert "self.player_detail_table = RosterTable()" in wrapper
    assert "self.player_detail_table.memberSelected.connect(self.load_member)" in wrapper
    assert "split.setStretchFactor(0, 3)" in wrapper
    assert "split.setStretchFactor(1, 2)" in wrapper

    assert '"urban_wilderness", "roster", "roster_badges.png"' in wrapper
    assert "def _roster_badge_sprite" in wrapper
    assert "badge.setPixmap(" in wrapper
    assert "from ui.ux_icons import icon" not in wrapper
    assert '"roster-players"' not in wrapper
    assert 'setProperty("rosterMetricBadge", True)' in wrapper
    assert "ordinal.hide()" in wrapper
    assert 'ordinal.setFixedSize(QSize(0, 0))' in wrapper
    assert "setMaximumHeight(148)" in wrapper
    assert Path("assets/themes/bff/urban_wilderness/roster/roster_badges.png").is_file()


def test_roster_embedded_pages_use_side_mounted_dedicated_back_arrow() -> None:
    wrapper = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert "back = QToolButton()" in wrapper
    assert "back.setIcon(_roster_back_icon())" in wrapper
    assert 'back.setToolTip("Back to Roster")' in wrapper
    assert 'QPushButton("Back to Roster")' not in wrapper
    assert "nav_rail.addStretch(1)" in wrapper
    assert "shell_layout.addLayout(nav_rail)" in wrapper
    assert '"urban_wilderness", "roster", "back_arrow.png"' in wrapper
    assert Path("assets/themes/bff/urban_wilderness/roster/back_arrow.png").is_file()


def test_roster_character_detail_is_profile_style_without_database_ids() -> None:
    wrapper = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert "def _show_character_detail" in wrapper
    assert "def _profile_html" in wrapper
    assert "self.character_detail_avatar" in wrapper
    assert 'setProperty("rosterProfileImage", True)' in wrapper
    assert '("Class",' in wrapper
    assert '("Race",' in wrapper
    assert '("Role",' in wrapper
    assert '("Teams",' in wrapper
    assert '("Readiness",' in wrapper
    assert '"Canonical ID"' not in wrapper
    assert '"Build ID"' not in wrapper
    assert "Builds and Assignments" not in wrapper
    assert '"CHARACTER\\nIMAGE"' in wrapper


def test_readiness_parchment_uses_field_journal_sketches_with_fixed_height() -> None:
    source = Path("ui/city_raid_readiness_page.py").read_text(encoding="utf-8")

    assert '"field_journal", "roster"' in source
    assert '"roster_people.jpg"' in source
    assert '"roster_team.jpg"' in source
    assert '"city_night", "roster"' not in source
    assert "self.setFixedHeight(150)" in source
    assert "Full-color city artwork belongs on dark surfaces" in source


def test_assignment_selected_spot_is_structured_profile_card_with_drawn_role_marks() -> None:
    source = Path("ui/city_raid_assignments_page.py").read_text(encoding="utf-8")

    assert 'detail.setProperty("selectedSpotCard", True)' in source
    assert 'self.selected_spot_title.setProperty("selectedSpotTitle", True)' in source
    assert 'self.selected_spot_role_icon.setProperty("selectedSpotRoleIcon", True)' in source
    assert "def _role_icon_name" in source
    assert "def _role_icon_pixmap" in source
    for role_key in ("healer", "tank", "dd", "support-dd"):
        assert f'"{role_key}"' in source
    assert 'from ui.ux_icons import set_button_icon' in source
    assert 'from ui.ux_icons import icon' not in source
    assert 'assets/icons/role-' not in source
    assert 'setProperty("semanticRoleMark", role_key)' in source
    assert 'form.addRow("Player", self.selected_player)' in source
    assert 'form.addRow("Character", self.selected_character)' in source
    assert 'form.addRow("Primary Assignment", self.selected_primary)' in source
    assert 'form.addRow("Secondary Assignment", self.selected_secondary)' in source
    assert 'form.addRow("Gear Needed", self.selected_gear)' in source
    assert 'form.addRow("Linked Build", self.selected_build)' in source
    assert 'edit_roles = QPushButton("Edit Duties")' in source


def test_city_key_remains_the_compatibility_storage_key_for_urban_wilderness() -> None:
    source = Path("services/accessibility_preferences.py").read_text(encoding="utf-8")

    assert 'VISUAL_THEME_RYLO_CITY = "rylo_city_night"' in source
    assert "VISUAL_THEME_URBAN_WILDERNESS = VISUAL_THEME_RYLO_CITY" in source
