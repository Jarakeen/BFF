from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_icon_polish_support
from ui import phase14_build_edit_return_support
from ui import phase14_build_focused_editors_support
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


def test_build_icon_polish_moves_new_build_to_header_and_uses_solid_gold() -> None:
    source = _source(phase14_build_icon_polish_support)

    assert "header.context_layout.addWidget(button)" in source
    assert 'button.setText("+ Create New Build")' in source
    assert "background: #C8A46A" in source
    assert "phase14GoldAction" in source


def test_build_icon_polish_uses_class_role_equipment_and_consumable_icons() -> None:
    source = _source(phase14_build_icon_polish_support)

    for icon_name in (
        "health",
        "shield",
        "set",
        "greaves",
        "heart_necklace",
        "leather_armor",
        "lunar_wand",
        "metal_boot",
        "metal_skirt",
        "ring",
        "spiked-shoulder-armor",
        "viking-helmet",
        "mailed-fist",
        "potion",
        "food",
    ):
        assert f'"{icon_name}"' in source
    assert "class_item.setIcon(class_icon)" in source
    assert "role_item.setIcon(role_icon)" in source


def test_build_skill_cards_restore_canonical_ability_art() -> None:
    source = _source(phase14_build_icon_polish_support)

    assert "load_skill_choices" in source
    assert '("assets", "AbilityIcons", "icons", "128"' in source
    assert "_skill_icon(name, 38)" in source
    assert "card.addWidget(_skill_row(index, skill))" in source


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
    assert 'if key == "TEAM":' in source
    assert "parent.hide()" in source
    assert "tab_bar.setVisible(tabs.currentIndex() != 0)" in source
    assert "layout.addWidget(nav)" in source


def test_rotation_visual_target_strengthens_context_intent_and_primary_action() -> None:
    source = _source(phase14_rotation_visual_target_support)

    assert '"CHARACTER": "Character"' in source
    assert "chip.setMinimumHeight(58)" in source
    assert "button.setMinimumHeight(132)" in source
    assert "button.setIconSize(QSize(38, 38))" in source
    assert "button.setMinimumHeight(64)" in source
    assert "background: #C8A46A" in source
    assert 'save_to_build = getattr(page, "save_rotation_to_build_button", None)' in source
    assert "save_to_build.hide()" in source


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
    assert "install_phase14_build_icon_polish_support()" in source
    assert "install_phase14_rotation_visual_target_support()" in source
    assert source.index("install_phase14_build_lifecycle_guard_support()") < source.index(
        "install_phase14_build_visual_target_support()"
    )
    assert source.index("install_phase14_build_visual_target_support()") < source.index(
        "install_phase14_build_icon_polish_support()"
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


def test_build_edit_save_and_cancel_return_to_phase14_library() -> None:
    source = _source(phase14_build_edit_return_support)

    assert "def _return_to_library(page) -> None:" in source
    assert "tabs.setCurrentIndex(0)" in source
    assert "def save_and_return(self) -> None:" in source
    assert "def cancel_and_return(self) -> None:" in source
    assert "apply_phase14_build_visual_target(page)" in source
    assert "_render_inspector(page)" in source


def test_rotation_context_polish_is_idempotent_across_page_reopen() -> None:
    source = _source(phase14_rotation_visual_target_support)

    assert 'value_label.property("phase14ContextPolished")' in source
    assert 'value_label.setProperty("phase14ContextPolished", True)' in source


def test_phase14_build_focused_editors_replace_normal_legacy_route() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert "class _GearDialog(_FocusedDialog):" in source
    assert "class _SkillsDialog(_FocusedDialog):" in source
    assert "class _ConsumablesDialog(_FocusedDialog):" in source
    assert "class _CPDialog(_FocusedDialog):" in source
    assert "class _NotesDialog(_FocusedDialog):" in source
    assert "class _IdentityDialog(_FocusedDialog):" in source
    assert "BuildsPage._phase14_legacy_edit_selected = original_edit_selected" in source
    assert "BuildsPage._edit_selected = edit_selected_phase14" in source


def test_phase14_build_dossier_uses_compact_group_cards_and_more_actions() -> None:
    source = _source(phase14_build_focused_editors_support)

    for icon_name in (
        "viking-helmet",
        "spiked-shoulder-armor",
        "leather-armor",
        "mailed-fist",
        "metal-skirt",
        "greaves",
        "metal-boot",
        "heart-necklace",
        "ring",
        "lunar-wand",
        "shield",
        "potion",
        "food",
    ):
        assert f'"{icon_name}"' in source
    assert 'more.setText("⋯  More actions")' in source
    assert 'save.setMinimumWidth(190)' in source
    assert 'profiles._baseline_card = _baseline_strip' in source


def test_phase14_focused_gear_editor_mutates_only_selected_build_section() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'self.build.Armor[slot] = value.to_dict()' in source
    assert 'self.build.Necklace = values["Neck"]' in source
    assert 'self.build.FrontBarWeapon = values["Main Hand"]' in source
    assert 'self.build.BackBarWeapon = values["Main Hand"]' in source
    assert "page._save()" in source
    assert "page._refresh_detail()" in source


def test_phase14_build_trait_icon_vocabulary_is_wired() -> None:
    source = _source(phase14_build_focused_editors_support)

    expected = {
        '"Powered": "Powered"',
        '"Charged": "Charged"',
        '"Precise": "Precise"',
        '"Defending": "Defending"',
        '"Sharpened": "Sharpened"',
        '"Decisive": "Decisive"',
        '"Nirnhoned": "drop"',
        '"Sturdy": "Sturdy"',
        '"Impenetrable": "Impenetrable"',
        '"Reinforced": "Reinforced"',
        '"Well-Fitted": "Well-fitted"',
        '"Invigorating": "Invigorating"',
        '"Divines": "Divines"',
        '"Healthy": "Health"',
        '"Arcane": "magic"',
        '"Robust": "Robust"',
        '"Bloodthirsty": "drop"',
        '"Harmony": "Harmony"',
        '"Triune": "Triune"',
        '"Protective": "Protective"',
        '"Swift": "Swift"',
    }
    for mapping in expected:
        assert mapping in source
    assert "_decorate_trait_combo(controller.trait_combo)" in source
    assert "row.addWidget(icon_label(trait_icon, 16))" in source


def test_phase14_icon_contract_normalizes_user_added_asset_names() -> None:
    source = _source(ux_icons)

    assert "def _normalized_icon_stem(value: str) -> str:" in source
    assert "root.iterdir()" in source
    assert '"stream-events": ("stream-events", "stream_events")' in source
    assert '"arcane": ("magic", "Arcane", "arcane")' in source
    assert '"nirnhoned": ("drop", "Nirnhoned", "nirnhoned")' in source
    assert '"bloodthirsty": ("drop", "Bloodthirsty", "bloodthirsty")' in source
    assert 'label.setProperty("semanticIconName", name)' in source
    assert 'button_widget.setProperty("semanticIconName", icon_name)' in source


def test_phase14_build_icons_are_reasserted_when_page_becomes_visible() -> None:
    source = _source(phase14_build_icon_polish_support)

    assert "original_show_event = ThemedBuildsPage.showEvent" in source
    assert "def show_event_with_phase14_icons(self, event):" in source
    assert "refresh_theme_icons(self)" in source
    assert "ThemedBuildsPage.showEvent = show_event_with_phase14_icons" in source


def test_phase14_rotation_front_page_is_the_four_requested_surfaces() -> None:
    command = Path(phase14_rotation_visual_target_support.__file__).with_name(
        "phase14_rotation_command_center_support.py"
    ).read_text(encoding="utf-8")
    visual = _source(phase14_rotation_visual_target_support)

    assert 'tab.setObjectName("phase14RotationFrontPage")' in command
    assert '_build_context(page)' in command
    assert '_build_intent_card(page)' in command
    assert '_build_obligations_card(page)' in command
    assert 'layout.addWidget(nav)' in visual
    assert 'card.header.hide()' in visual
    assert 'card.set_icon("rotations")' in visual
    assert 'card.set_icon("field-office")' in visual
    assert "refresh_theme_icons(page)" in visual


def test_phase14_rotation_intents_and_settings_match_target_card_controls() -> None:
    command = Path(phase14_rotation_visual_target_support.__file__).with_name(
        "phase14_rotation_command_center_support.py"
    ).read_text(encoding="utf-8")

    assert "button = QToolButton()" in command
    assert "ToolButtonTextUnderIcon" in command
    assert 'set_button_icon(button, values["icon"], size=36)' in command
    assert 'set_button_icon(edit, "pen", size=18)' in command
    assert 'These settings shape your rotation and ability priorities.' in command
    assert 'Custom rules, conditionals, and resource management.' in command
    assert 'page.generate_button.setText("▶  Generate Rotation")' in command


def test_phase14_rotation_command_center_imports_qt_for_tool_button_style() -> None:
    command = Path(phase14_rotation_visual_target_support.__file__).with_name(
        "phase14_rotation_command_center_support.py"
    ).read_text(encoding="utf-8")

    assert "from PySide6.QtCore import Qt" in command
    assert "Qt.ToolButtonStyle.ToolButtonTextUnderIcon" in command


def test_phase14_rotation_headings_are_large_gold_and_reassert_result_icons() -> None:
    visual = _source(phase14_rotation_visual_target_support)
    command = Path(phase14_rotation_visual_target_support.__file__).with_name(
        "phase14_rotation_command_center_support.py"
    ).read_text(encoding="utf-8")

    assert 'page.phase14_generated_settings_heading = QLabel("Generated Settings")' in command
    assert "def _polish_primary_headings(page) -> None:" in visual
    assert '"color: #C8A46A; font-size: 22px; font-weight: 700;"' in visual
    assert '"color: #C8A46A; font-size: 20px; font-weight: 700;"' in visual
    assert "card.icon_label.setFixedSize(30, 30)" in visual
    assert "def _polish_result_nav(page) -> None:" in visual
    assert "set_button_icon(button, icon_name, size=24)" in visual


def test_phase14_semantic_icons_use_explicit_svg_renderer() -> None:
    source = _source(ux_icons)

    assert "def _source_svg_pixmap(path_text: str, size: int) -> QPixmap:" in source
    assert "QSvgRenderer" in source
    assert "def _strip_full_canvas_background(svg: str) -> str:" in source
    assert "return _source_svg_icon(path)" in source


def test_semantic_icon_refresh_clears_miss_cache_and_uses_native_svg_fallback() -> None:
    source = _source(ux_icons)

    assert "icon_path.cache_clear()" in source
    assert "direct = QIcon(str(path))" in source
    assert "if not direct.isNull():" in source
    assert "rendered = _source_svg_icon(path)" in source
