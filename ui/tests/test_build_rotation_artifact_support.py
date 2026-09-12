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


def test_support_is_installed_after_rotation_layout_support() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    layout_call = source.index("install_rotation_dashboard_layout_support()")
    artifact_call = source.index("install_build_rotation_artifact_support()")
    assert layout_call < artifact_call
