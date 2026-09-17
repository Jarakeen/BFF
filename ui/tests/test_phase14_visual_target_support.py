from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_lifecycle_guard_support
from ui import phase14_build_visual_target_support
from ui import phase14_rotation_visual_target_support
from ui import ux_icons
from ui.components import foundry_card


def _source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def test_build_visual_target_keeps_one_visible_new_build_action_and_right_inspector() -> None:
    source = _source(phase14_build_visual_target_support)

    assert "def apply_phase14_build_visual_target(page) -> None:" in source
    assert 'source = getattr(page, "create_character_button", None)' in source
    assert "source.hide()" in source
    assert "parent.hide()" in source
    assert "inspector.show()" in source
    assert "inspector.setMinimumWidth(500)" in source
    assert "splitter.setChildrenCollapsible(False)" in source
    assert "splitter.setSizes([900, 650])" in source


def test_build_visual_target_runs_after_actual_themed_build_ui_chain() -> None:
    source = _source(phase14_build_visual_target_support)

    assert "from ui.themed_builds_page import BuildsPage as ThemedBuildsPage" in source
    assert "original_themed_build_ui = ThemedBuildsPage._build_ui" in source
    assert "def build_themed_with_final_visual_target(self):" in source
    assert "apply_phase14_build_visual_target(self)" in source
    assert "ThemedBuildsPage._build_ui = build_themed_with_final_visual_target" in source


def test_build_lifecycle_repair_restores_inspector_after_legacy_wrappers() -> None:
    source = _source(phase14_build_lifecycle_guard_support)

    assert "def _restore_inspector(page) -> None:" in source
    assert "inspector_support._render_inspector(page)" in source
    assert "right.setMinimumWidth(500)" in source
    assert "_restore_inspector(page)" in source


def test_rotation_visual_target_moves_results_below_builder_and_hides_team_chip() -> None:
    source = _source(phase14_rotation_visual_target_support)

    for label, icon_name in (
        ("Timeline", "hourglass"),
        ("Uptime & Resources", "filter"),
        ("Explanations", "binoculars"),
        ("Compare", "scales"),
        ("Save & Export", "download"),
    ):
        assert f'"{label}"' in source
        assert f'"{icon_name}"' in source
    assert 'get("TEAM")' in source
    assert "team_label.parentWidget().hide()" in source
    assert "tab_bar.setVisible(tabs.currentIndex() != 0)" in source
    assert "layout.addWidget(nav)" in source


def test_rotation_visual_target_preserves_legacy_builder_widget_lifetime() -> None:
    source = _source(phase14_rotation_visual_target_support)

    assert "page._phase14_preserved_legacy_builder = legacy_builder" in source
    assert "legacy_builder.deleteLater = legacy_builder.hide" in source
    assert "layout_support.install_phase14_rotation_command_center = install_target" in source


def test_rotation_visual_target_reasserts_at_real_page_show_boundary() -> None:
    source = _source(phase14_rotation_visual_target_support)

    assert "from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage" in source
    assert "original_show_event = CanonicalRotationDashboardPage.showEvent" in source
    assert "def show_event_with_visual_target(self, event) -> None:" in source
    assert "apply_phase14_rotation_visual_target(self)" in source
    assert "CanonicalRotationDashboardPage.showEvent = show_event_with_visual_target" in source


def test_visual_target_support_is_composed_before_page_construction() -> None:
    source = _source(application_workspace_bootstrap)

    assert "install_phase14_build_visual_target_support()" in source
    assert "install_phase14_rotation_visual_target_support()" in source
    assert source.index("install_phase14_build_lifecycle_guard_support()") < source.index(
        "install_phase14_build_visual_target_support()"
    )


def test_icon_service_accepts_separator_variants_and_field_office_filename() -> None:
    source = _source(ux_icons)

    assert '"field office"' in source
    assert 'candidate.replace("_", "-")' in source
    assert 'candidate.replace("-", " ")' in source
    assert '"swapping": ("swapping", "switch-weapon")' in source


def test_foundry_card_never_prints_missing_icon_name_as_heading_text() -> None:
    source = _source(foundry_card)

    assert "semantic_qicon(icon)" in source
    assert "if value.isNull():" in source
    assert "self.icon_label.setText(icon)" not in source
