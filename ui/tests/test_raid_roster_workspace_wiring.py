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

    assert "install_roster_top_back_control(roster_workspace)" in source
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


def test_roster_detail_back_arrow_is_contextual_top_strip_control_without_squeezing_content() -> None:
    wrapper = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")
    support = Path("ui/roster_top_back_control_support.py").read_text(encoding="utf-8")

    assert 'QPushButton("Back to Roster")' not in wrapper
    assert "install_roster_top_back_control" in support
    assert 'back.setObjectName("rosterTopBackButton")' in support
    assert 'back.setProperty("rosterBackButton", True)' in support
    assert 'back.setToolTip("Back to Roster")' in support
    assert '"back_arrow.png"' in support
    assert "back = QToolButton(metrics)" in support
    assert "metrics_layout.addWidget(back, 0, 0" in support
    assert "for column, card in enumerate(page.metric_cards.values(), start=1)" in support
    assert "metrics_layout.setColumnMinimumWidth(0, 62 if visible else 0)" in support
    assert "stack.currentChanged.connect(sync_visibility)" in support
    assert "back.setVisible(visible)" in support
    assert "class _BackArrowAnchor(QObject)" not in support
    assert "self.button.move(x, y)" not in support
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
    assert 'form.addRow("Buffs / Debuffs", self.selected_support)' in source
    assert 'form.addRow("Utility / Mechanics", self.selected_utility)' in source
    assert 'form.addRow("Planned Gear", self.selected_gear)' in source
    assert 'form.addRow("Linked Build", self.selected_build)' in source
    assert 'form.addRow("Notes", self.selected_notes)' in source


def test_city_key_remains_the_compatibility_storage_key_for_urban_wilderness() -> None:
    source = Path("services/accessibility_preferences.py").read_text(encoding="utf-8")

    assert 'VISUAL_THEME_RYLO_CITY = "rylo_city_night"' in source
    assert "VISUAL_THEME_URBAN_WILDERNESS = VISUAL_THEME_RYLO_CITY" in source


def test_roster_character_avatar_is_click_editable_and_character_owned() -> None:
    wrapper = Path("ui/city_raid_roster_workspace_page.py").read_text(encoding="utf-8")
    catalog = Path("services/build_catalog_service.py").read_text(encoding="utf-8")

    assert 'self.character_detail_avatar.mousePressEvent = self._avatar_mouse_press' in wrapper
    assert 'class _CharacterAvatarDialog(QDialog):' in wrapper
    assert 'get_resource_path(*_AVATAR_ROOT)' in wrapper
    assert 'reference = f"assets/avatar/{path.name}"' in wrapper
    assert 'target_root = get_data_dir() / "avatar"' in wrapper
    assert 'catalog.set_character_avatar(' in wrapper
    assert 'character.get("avatar_path")' in wrapper
    assert 'def set_character_avatar(' in catalog
    assert 'updated["avatar_path"] = normalized_path' in catalog


def test_current_teams_editor_exposes_and_persists_discord_link() -> None:
    source = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")

    assert "self.team_discord = QLineEdit()" in source
    assert 'form.addRow("Discord", self.team_discord)' in source
    assert "self.team_discord.setText(schedule.DiscordUrl if schedule else \"\")" in source
    assert "DiscordUrl=_clean(self.team_discord.text())" in source


def test_optimizer_handoff_targets_current_roster_workspace() -> None:
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")
    roster = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")

    method = main_window.split(
        "def _send_optimized_team_to_roster", 1
    )[1].split("def _open_player_builds", 1)[0]

    assert 'self.pages.get("roster_workspace")' in method
    assert 'self.show_page("roster_workspace")' in method
    assert 'self.show_page("roster_page")' not in method
    assert 'load_optimizer_plan' in method

    assert 'FoundryCard("Optimizer Plan", "compass")' in roster
    assert "def load_optimizer_plan(self, plan)" in roster
    assert 'show_detail("teams")' in roster
    assert "Saved team membership was not changed." in roster


def test_comp_builder_handoff_targets_current_roster_workspace() -> None:
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")
    roster = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")

    method = main_window.split(
        "def _show_generated_roster_plan", 1
    )[1].split("def _confirm_collectible_navigation", 1)[0]

    assert 'GeneratedRosterDraftService' in method
    assert '.load_plan(plan_name)' in method
    assert 'self.pages.get("roster_workspace")' in method
    assert 'self.show_page("roster_workspace")' in method
    assert 'self.show_page("roster_page")' not in method
    assert 'source="Comp Builder"' in method
    assert "load_external_team_plan" in method

    assert 'def load_external_team_plan(' in roster
    assert 'def load_optimizer_plan(self, plan)' in roster
    assert 'FoundryCard("Incoming Team Plan", "compass")' in roster


def test_navigation_has_app_wide_unsaved_change_contract() -> None:
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    plan = Path("ui/raid_plan_persistence_page.py").read_text(encoding="utf-8")

    assert "def _confirm_unsaved_navigation(self, target_page: str) -> bool:" in main
    assert "QMessageBox.StandardButton.Save" in main
    assert "QMessageBox.StandardButton.Discard" in main
    assert "QMessageBox.StandardButton.Cancel" in main
    assert "if not self._confirm_unsaved_navigation(page_name):" in main
    assert "def has_pending_changes(self) -> bool:" in plan
    assert "def save_pending_changes(self) -> bool:" in plan
    assert "def discard_pending_changes(self) -> bool:" in plan


def test_personnel_exposes_social_fields_and_discord_screenshot_intake() -> None:
    record = Path("widgets/roster_record.py").read_text(encoding="utf-8")
    workspace = Path("ui/raid_roster_workspace_page.py").read_text(encoding="utf-8")
    intake = Path("ui/discord_profile_screenshot_import.py").read_text(encoding="utf-8")

    assert 'form.addRow("Discord", self.discord_name)' in record
    assert 'form.addRow("YouTube", self.youtube)' in record
    assert 'form.addRow("Twitch", self.twitch)' in record
    assert '"Import Discord Screenshot…"' in record
    assert "screenshotImportRequested = Signal()" in record
    assert "self.record.screenshotImportRequested.connect(self._import_discord_profile_screenshot)" in workspace
    assert "dialog.apply_to_record()" in intake
    assert "create_member" not in intake
    assert "update_member" not in intake
    assert "Nothing is saved automatically." in intake
