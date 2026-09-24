from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_inspector_support
from ui import phase14_build_focused_editors_support
from ui import phase14_build_profile_support
from ui import phase14_builds_command_center_support
from ui import phase14_rotation_command_center_support
from ui import rotation_dashboard_layout_support


def _source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def test_phase14_build_command_center_is_composed_after_existing_build_features() -> None:
    source = _source(application_workspace_bootstrap)

    assert "install_phase14_builds_command_center_support()" in source
    assert "install_phase14_build_profile_support()" in source
    assert "install_phase14_build_inspector_support()" in source
    assert "install_phase14_build_creation_bridge()" not in source
    assert source.index("install_build_reuse_template_support()") < source.index(
        "install_phase14_builds_command_center_support()"
    )
    assert source.index("install_phase14_builds_command_center_support()") < source.index(
        "install_phase14_build_profile_support()"
    )
    assert source.index("install_phase14_build_profile_support()") < source.index(
        "install_phase14_build_inspector_support()"
    )


def test_build_command_center_exposes_selected_library_views_and_filters() -> None:
    source = _source(phase14_builds_command_center_support)

    assert '("All", "Mine", "Team", "Comp Builds", "Templates", "Favorites", "Archive")' in source
    assert 'setPlaceholderText("Search builds…")' in source
    assert '("Class", page.phase14_class_filter)' in source
    assert '("Role", page.phase14_role_filter)' in source
    assert '("Content", page.phase14_content_filter)' in source
    assert '("Source", page.phase14_source_filter)' in source
    assert 'page.phase14_source_filter.addItem("Comp Builds", "comp")' in source
    assert 'page.phase14_source_filter.addItem("Saved Builds", "saved")' in source
    assert "self.splitter.replaceWidget(0, command_center)" in source
    assert "setUsesScrollButtons(True)" in source


def test_phase14_new_build_reuses_existing_easy_mode_action_without_second_wrapper() -> None:
    source = _source(phase14_builds_command_center_support)

    assert 'existing = getattr(page, "create_character_button", None)' in source
    assert "page.phase14_create_build_button.clicked.connect(existing.click)" in source
    assert 'action_host = getattr(page, "new_build_action_host", None)' in source
    assert "action_host.hide()" in source


def test_build_profile_support_uses_additive_sidecar_and_baseline() -> None:
    source = _source(phase14_build_profile_support)

    assert 'get_data_dir() / "build_profiles.json"' in source
    assert 'FoundryCard(title, "◆")' in source
    assert 'build_profile_exception_count(build, profile)' in source
    assert '"My Build" if profile.ownership == "mine"' in source
    assert 'favorite=not profile.favorite' in source
    assert 'archived=not profile.archived' in source


def test_build_profile_support_can_assign_mine_or_team_ownership_by_build_id() -> None:
    source = _source(phase14_build_profile_support)

    assert 'class _OwnershipDialog(QDialog):' in source
    assert 'self.ownership.addItem("My Build", "mine")' in source
    assert 'self.ownership.addItem("Team / Other Player", "team")' in source
    assert 'self.source_owner = QLineEdit()' in source
    assert 'build_id = _build_id(page, build)' in source
    assert 'ownership=ownership' in source
    assert 'source_owner=source_owner' in source
    assert 'FoundryButton("Ownership"' in source
    assert '"Team" if ownership == "team" else "Mine"' in source


def test_phase14_build_inspector_uses_selected_section_tabs() -> None:
    source = _source(phase14_build_inspector_support)

    for label in ("Overview", "Gear", "Skills", "CP", "Consumables", "Scribing", "Notes"):
        assert f'"{label}"' in source
    for label in ("Armor", "Jewelry", "Front Bar", "Back Bar"):
        assert f'"{label}"' in source
    assert "page.detail_layout.addWidget(tabs, 1)" in source
    assert "_open_workspace_tab(page, workspace_tab)" in source
    assert 'tabs.tabBar().setVisible(not library_mode)' in source
    assert '"Character Progression", workspace_tab=2' in source
    assert '"Open Scribed Skills", workspace_tab=3' in source


def test_rotation_command_center_is_installed_by_dashboard_layout() -> None:
    source = _source(rotation_dashboard_layout_support)

    assert "install_phase14_rotation_command_center" in source
    assert "install_phase14_rotation_command_center(page)" in source


def test_rotation_command_center_has_intents_obligations_and_result_gate() -> None:
    source = _source(phase14_rotation_command_center_support)

    for label in ("Safe Progression", "Balanced", "Maximum Output"):
        assert label in source
    for label in ("Build skills", "Gear procs", "Team duties", "Pressure windows", "Advanced rules"):
        assert label in source
    assert 'page.generate_button.setMinimumHeight(60)' in source
    assert '_enable_result_tabs(page, False)' in source
    assert 'page.phase14_rotation_customized_label.setText("Customized" if customized else "Preset defaults")' in source
    assert 'page.phase14_rotation_reset_button.setVisible(customized)' in source


def test_rotation_context_is_icon_led_summary_with_explicit_edit_disclosure() -> None:
    source = _source(phase14_rotation_command_center_support)

    assert '("CHARACTER", "user", "character_combo")' in source
    assert '("BUILD", "builds", "build_combo")' in source
    assert '("TRIAL", "trial", "rotation_content_combo")' in source
    assert '("BOSS", "boss", "rotation_boss_combo")' in source
    assert '("DIFFICULTY", "crossed-swords", "rotation_threshold_difficulty_combo")' in source
    assert 'page.phase14_context_value_labels = {}' in source
    assert 'page.phase14_context_edit_button = QPushButton("Edit Context")' in source
    assert "page.phase14_context_controls_panel.hide()" in source
    assert "_refresh_context_summary(page)" in source


def test_rotation_intents_settings_and_obligations_use_requested_semantic_icons() -> None:
    source = _source(phase14_rotation_command_center_support)

    for icon_name in (
        "shield",
        "scales",
        "optimization",
        "cog",
        "swapping",
        "sword",
        "drop",
        "book-open-text",
        "roster",
        "warning",
        "field-office",
        "uptime",
    ):
        assert f'"{icon_name}"' in source
    assert 'button.setMinimumHeight(118)' in source
    assert 'row.setMinimumHeight(48)' in source
    assert 'button.setMinimumHeight(54)' in source


def test_rotation_result_tabs_have_clean_labels_and_icons() -> None:
    source = _source(phase14_rotation_command_center_support)

    for label, icon_name in (
        ("Timeline", "hourglass"),
        ("Uptime & Resources", "filter"),
        ("Explanations", "binoculars"),
        ("Compare", "scales"),
        ("Save & Export", "download"),
    ):
        assert f'"{label}"' in source
        assert f'"{icon_name}"' in source
    assert "Uptime_Resources" not in source
    assert "Advanced execution_sustain" not in source


def test_advanced_rules_does_not_reparent_execution_panel() -> None:
    source = _source(phase14_rotation_command_center_support)

    assert '_obligation_row(page, "Advanced rules", "Priority and conditional logic.", "—", _build_rules_detail())' in source
    assert 'page.rotation_advanced_panel' not in source


def test_phase14_final_build_header_keeps_ready_checkbox_visible() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'ready = QCheckBox("Ready")' in source
    assert "ready.setChecked(bool(getattr(build, \"ReadyForRaid\", False)))" in source
    assert "page._set_build_ready(selected, checked)" in source


def test_phase14_build_overview_restores_context_variant_access() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'FoundryCard("Context Variants", "swapping")' in source
    assert '"Edit Context Variants"' in source
    assert "page._open_phase14_legacy_build_editor()" in source
    assert "inspector._overview_tab = overview_with_context_variants" in source


def test_phase14_selected_build_identity_uses_compact_hero_title_not_page_title() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'title.setProperty("heroTitle", True)' in source
    assert 'title.setProperty("pageTitle", True)' not in source


def test_build_command_center_keeps_comp_tab_and_source_filter_in_sync() -> None:
    source = _source(phase14_builds_command_center_support)

    assert 'if mode == "Comp Builds":' in source
    assert 'wanted = source_filter.findData("comp")' in source
    assert 'source_filter.setCurrentIndex(wanted if wanted >= 0 else 0)' in source
    assert 'if selected_source == "comp" and build_kind != "comp":' in source
    assert 'if selected_source == "saved" and build_kind == "comp":' in source
    assert "setUsesScrollButtons(True)" in source
    assert "setMinimumWidth(650)" in source


def test_comp_build_planning_state_is_visible_in_focused_build_editors() -> None:
    source = _source(phase14_build_focused_editors_support)

    assert 'getattr(build, "PlannedGearSets", ())' in source
    assert '"Comp Maker plan • exact slots not assigned yet"' in source
    assert 'FoundryCard("Comp Plan", "clipboard")' in source
    assert '"Planned in Comp Maker. These sets are not assigned to exact gear slots yet."' in source
    assert 'getattr(build, "PlannedSkills", ())' in source
    assert 'FoundryCard("Comp Planned Skills", "clipboard")' in source
    assert '"Planned in Comp Maker. These are requirements/recommendations, not exact bar slots."' in source
    assert '"Planned in Comp Maker. These skills are not assigned to exact bar slots yet."' in source


def test_template_application_switches_visible_phase14_library_to_all_builds() -> None:
    source = Path("ui/build_reuse_template_support.py").read_text(encoding="utf-8")

    assert 'FoundryButton("Create Saved Build…"' in source
    assert 'if tabs.tabText(index) == "All":' in source
    assert 'tabs.setCurrentIndex(index)' in source
    assert 'Created saved Build' in source


def test_template_table_selection_updates_exact_template_detail_without_hidden_signal_dependency() -> None:
    source = Path("ui/phase14_builds_command_center_support.py").read_text(encoding="utf-8")

    assert "page.roster_list.blockSignals(True)" in source
    assert "page._select_member(source_row)" in source
    assert "currentCellChanged.connect" in source
    assert "template_class" in source
    assert "template_role" in source
    assert "selected_class" in source
    assert "selected_role" in source
