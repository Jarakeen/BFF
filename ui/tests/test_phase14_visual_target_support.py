from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_icon_polish_support
from ui import phase14_build_edit_return_support
from ui import phase14_build_focused_editors_support
from ui import phase14_build_lifecycle_guard_support
from ui import phase14_build_visual_target_support
from ui import phase14_rotation_command_center_support
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


def test_visual_target_support_is_composed_before_page_construction() -> None:
    source = _source(application_workspace_bootstrap)

    assert "install_phase14_build_visual_target_support()" in source
    assert "install_phase14_build_icon_polish_support()" in source
    assert "install_phase14_rotation_visual_target_support()" not in source
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
    command = _source(phase14_rotation_command_center_support)

    assert 'tab.setObjectName("phase14RotationFrontPage")' in command
    assert '_build_context(page)' in command
    assert '_build_intent_card(page)' in command
    assert '_build_obligations_card(page)' in command


def test_phase14_rotation_intents_and_settings_match_target_card_controls() -> None:
    command = _source(phase14_rotation_command_center_support)

    assert "button = QToolButton()" in command
    assert "ToolButtonTextUnderIcon" in command
    assert 'set_button_icon(button, values["icon"], size=36)' in command
    assert 'set_button_icon(edit, "pen", size=18)' in command
    assert 'These settings shape your rotation and ability priorities.' in command
    assert 'Custom rules, conditionals, and resource management.' in command
    assert 'page.generate_button.setText("▶  Generate Rotation")' in command


def test_phase14_rotation_command_center_imports_qt_for_tool_button_style() -> None:
    command = _source(phase14_rotation_command_center_support)

    assert "from PySide6.QtCore import Qt" in command
    assert "Qt.ToolButtonStyle.ToolButtonTextUnderIcon" in command


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


def test_foundry_semantic_icons_are_gold_and_backing_tiles_are_stripped() -> None:
    source = _source(ux_icons)

    assert '_FOUNDRY_DEFAULT = "#C8A46A"' in source
    assert '_FOUNDRY_DISABLED = "#73777C"' in source
    assert "def _foundry_icon" in source
    assert "themed = _rylo_icon(path) if _is_rylo_theme() else _foundry_icon(path)" in source
    assert "_strip_full_canvas_background(svg)" in source
    assert '"cog": ("cog", "gears")' in source


def test_phase14_build_identity_editor_exposes_vampire_and_werewolf() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'self.vampire = QCheckBox("Vampire")' in source
    assert 'self.werewolf = QCheckBox("Werewolf")' in source
    assert 'form.addRow("World state", affiliation)' in source
    assert 'self.build.Vampire = self.vampire.isChecked()' in source
    assert 'self.build.Werewolf = self.werewolf.isChecked()' in source
    assert 'self.werewolf.setChecked(False) if checked else None' in source
    assert 'self.vampire.setChecked(False) if checked else None' in source
