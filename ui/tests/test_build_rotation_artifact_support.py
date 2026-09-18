from pathlib import Path

from ui import build_rotation_artifact_support


def _source() -> str:
    return Path(build_rotation_artifact_support.__file__).read_text(encoding="utf-8")


def test_rotation_page_can_save_only_a_completed_plan_to_build() -> None:
    source = _source()

    assert 'QPushButton("Save Rotation to Build")' in source
    assert "self.rotation_plan is None or not self.rotation_plan.actions" in source
    assert "resolve_canonical_build_id" in source
    assert "save_rotation(" in source
    assert 'f"Saved rotation to {character} • {build_name}' in source


def test_build_workspace_rotation_tab_is_conditional() -> None:
    source = _source()

    assert 'self.build_tabs.addTab(' in source
    assert '"Rotation",' in source
    assert "self.build_tabs.setTabVisible(rotation_index, False)" in source
    assert "page.build_tabs.setTabVisible(tab_index, True)" in source
    assert "page.build_tabs.setTabVisible(tab_index, False)" in source
    assert "workspace_tabs" not in source
    assert "page.build_rotation_artifacts.get_rotation(build_id or \"\")" in source


def test_saved_rotation_renders_timeline_and_generation_setup() -> None:
    source = _source()

    assert '["Time", "Bar", "Action", "Type", "Notes"]' in source
    assert 'payload["setup"] = jsonable(setup)' in source
    assert 'payload["encounter_id"]' in source
    assert 'setup["recovery_resource"]' in source
    assert "canonical_threshold_projection_policy" in source
    assert "canonical_dd_evaluation_policy" in source


def test_support_wraps_rotation_after_native_layout_construction() -> None:
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )

    assert "install_build_rotation_artifact_support()" in bootstrap
    assert "install_rotation_dashboard_layout(self)" in dashboard
    assert "install_rotation_dashboard_layout_support()" not in bootstrap


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
