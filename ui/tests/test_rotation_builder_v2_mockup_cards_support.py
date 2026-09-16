from pathlib import Path

import ui.rotation_builder_v2_mockup_cards_support as mockup_cards
import ui.rotation_builder_v2_runtime_repairs_support as runtime_repairs
import ui.rotation_dashboard_layout_support as layout_support


def test_rotation_uses_safe_runtime_repairs_after_compact_context() -> None:
    source = Path(layout_support.__file__).read_text(encoding="utf-8")

    assert "install_rotation_builder_v2_mockup_cards" not in source
    assert "install_rotation_builder_v2_runtime_repairs" in source
    assert source.index("install_rotation_builder_v2_compact_context(page)") < source.index(
        "install_rotation_builder_v2_runtime_repairs(page)"
    )


def test_duration_evidence_is_flattened_without_rebuilding_the_workspace() -> None:
    source = Path(runtime_repairs.__file__).read_text(encoding="utf-8")

    assert "def _flatten_duration_evidence(page)" in source
    assert 'outer = _card(page, "Duration & Uptime Evidence")' in source
    assert "inner.setParent(page)" in source
    assert "layout.addWidget(inner, row, column, row_span, column_span)" in source


def test_recovery_heavy_repair_reuses_saved_build_weapon_bridge() -> None:
    source = Path(runtime_repairs.__file__).read_text(encoding="utf-8")

    assert "RotationSavedBuildWeaponAttackEvaluationService" in source
    assert "weapon_resolution = weapon_service.resolve(" in source
    assert "character_build = weapon_resolution.build" in source
    assert "heavy_service.restoration_resolver_for_plan(" in source


def test_compare_mockup_reuses_live_combo_and_table() -> None:
    source = Path(mockup_cards.__file__).read_text(encoding="utf-8")

    assert 'card = FoundryCard("Compare Rotations", "◇")' in source
    assert "combo = page.rotation_compare_build_combo" in source
    assert "table = page.rotation_compare_table" in source
    assert 'page.rotation_compare_by_combo.addItem("Builds")' in source
    assert "page.rotation_compare_by_combo.setEnabled(False)" in source


def test_save_export_mockup_keeps_real_buttons_and_disables_unimplemented_controls() -> None:
    source = Path(mockup_cards.__file__).read_text(encoding="utf-8")

    assert "save_button = page.rotation_v2_save_button" in source
    assert "export_button = page.rotation_v2_export_pdf_button" in source
    assert 'save = FoundryCard("Save Rotation", "◆")' in source
    assert 'export = FoundryCard("Export Options", "✦")' in source
    assert 'share = FoundryCard("Share", "◇")' in source
    assert "team_library.setEnabled(False)" in source
    assert "copy_link.setEnabled(False)" in source
    assert "share_code.setEnabled(False)" in source
