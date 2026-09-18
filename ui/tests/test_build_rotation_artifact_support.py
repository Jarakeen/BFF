from pathlib import Path

from ui import build_rotation_artifact_support


def _source() -> str:
    return Path(build_rotation_artifact_support.__file__).read_text(encoding="utf-8")


def test_saved_rotation_adapter_does_not_import_or_patch_rotation_builder() -> None:
    source = _source()

    assert "CanonicalRotationDashboardPage" not in source
    assert "Save Rotation to Build" not in source
    assert "rotation_plan" not in source
    assert "BuildsPage._build_ui = builds_ui_with_rotation_tab" in source


def test_build_workspace_rotation_tab_is_conditional() -> None:
    source = _source()

    assert 'self.build_tabs.addTab(' in source
    assert '"Rotation",' in source
    assert "self.build_tabs.setTabVisible(rotation_index, False)" in source
    assert "page.build_tabs.setTabVisible(tab_index, True)" in source
    assert "page.build_tabs.setTabVisible(tab_index, False)" in source
    assert "workspace_tabs" not in source
    assert "page.build_rotation_artifacts.get_rotation(build_id or \"\")" in source


def test_saved_rotation_renders_existing_timeline_and_setup() -> None:
    source = _source()

    assert '["Time", "Bar", "Action", "Type", "Notes"]' in source
    assert 'artifact.get("setup")' in source
    assert 'artifact.get("encounter_id")' in source
    assert "page.build_rotation_artifacts.get_rotation" in source


def test_support_is_owned_by_bootstrap_without_constructing_rotation_builder() -> None:
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert "install_build_rotation_artifact_support()" in bootstrap
    assert "CanonicalRotationDashboardPage" not in main_window
    assert '"rotations": CanonicalRotationDashboardPage(),' not in main_window
    assert "install_phase14_rotation_visual_target_support()" not in bootstrap


def test_phase14_build_dossier_labels_base_skills_and_cp_as_inherited_baseline() -> None:
    source = Path("ui/phase14_build_focused_editors_support.py").read_text(encoding="utf-8")

    assert '"Base Front Bar"' in source
    assert '"Base Back Bar"' in source
    assert '"Edit Base Skills"' in source
    assert '"Base Champion Points"' in source
    assert '"Edit Base CP"' in source
    assert "Context variants inherit these base skill bars until overridden." in source
    assert "Context variants inherit these base Champion Points until overridden." in source


def test_phase14_build_dossier_owns_character_progression_and_legacy_editor_is_fallback() -> None:
    focused = Path("ui/phase14_build_focused_editors_support.py").read_text(encoding="utf-8")
    inspector = Path("ui/phase14_build_inspector_support.py").read_text(encoding="utf-8")
    legacy = Path("ui/build_editor_inline_compat.py").read_text(encoding="utf-8")

    assert "def _progression_tab(page, build)" in focused
    assert '"Passive Skills"' in focused
    assert '"Passive Champion Points"' in focused
    assert '"Edit Passive Skills"' in focused
    assert '"Edit Passive CP"' in focused
    assert "CharacterProgressionService(catalog_service).save" in focused
    assert 'tabs.addTab(_progression_tab(page, build), "Progression")' in inspector
    assert '"Legacy Build Editor (Fallback)"' in focused
    assert "tabs.setTabVisible(1, True)" in focused
    assert "for legacy_index in (1, 2, 3):" in legacy
    assert "tabs.setTabVisible(legacy_index, False)" in legacy


def test_character_progression_has_global_buy_all_actions() -> None:
    source = Path("ui/phase5_build_ui_support.py").read_text(encoding="utf-8")

    assert '"Buy All Passive Skills"' in source
    assert '"Buy All Passive CP"' in source
    assert "for check in self._line_checks.values():" in source
    assert 'check.setChecked(True)' in source
    assert '_set_progression_spins(all_skill_spins, "max")' in source
    assert '_set_progression_spins(all_cp_spins, "max")' in source
