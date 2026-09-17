from __future__ import annotations

from pathlib import Path

from ui import application_workspace_bootstrap
from ui import phase14_build_creation_bridge
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
    assert "install_phase14_build_creation_bridge()" in source
    assert source.index("install_build_reuse_template_support()") < source.index(
        "install_phase14_builds_command_center_support()"
    )
    assert source.index("install_phase14_builds_command_center_support()") < source.index(
        "install_phase14_build_profile_support()"
    )
    assert source.index("install_phase14_build_profile_support()") < source.index(
        "install_phase14_build_creation_bridge()"
    )


def test_build_command_center_exposes_selected_library_views_and_filters() -> None:
    source = _source(phase14_builds_command_center_support)

    assert '("All", "Mine", "Team", "Templates", "Favorites", "Archive")' in source
    assert 'setPlaceholderText("Search builds…")' in source
    assert '("Class", page.phase14_class_filter)' in source
    assert '("Role", page.phase14_role_filter)' in source
    assert '("Content", page.phase14_content_filter)' in source


def test_build_profile_support_uses_additive_sidecar_and_baseline() -> None:
    source = _source(phase14_build_profile_support)

    assert 'get_data_dir() / "build_profiles.json"' in source
    assert 'FoundryCard(title, "◆")' in source
    assert 'build_profile_exception_count(build, profile)' in source
    assert '"My Build" if profile.ownership == "mine"' in source
    assert 'favorite=not profile.favorite' in source
    assert 'archived=not profile.archived' in source


def test_phase14_new_build_uses_existing_easy_mode_panel() -> None:
    source = _source(phase14_build_creation_bridge)

    assert 'panel = getattr(self, "new_build_panel", None)' in source
    assert "button.clicked.connect(panel.open_for_creation)" in source
    assert 'old_host = getattr(self, "new_build_action_host", None)' in source
    assert "old_host.hide()" in source


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
    assert 'page.generate_button.setMinimumHeight(54)' in source
    assert '_enable_result_tabs(page, False)' in source
    assert 'page.phase14_rotation_customized_label.setText("Customized" if customized else "Preset defaults")' in source
    assert 'page.phase14_rotation_reset_button.setVisible(customized)' in source


def test_advanced_rules_does_not_reparent_execution_panel() -> None:
    source = _source(phase14_rotation_command_center_support)

    assert '_obligation_row(page, "Advanced rules", "Custom ability priorities and conditional logic.", "—", _build_rules_detail())' in source
    assert '_obligation_row(page, "Advanced rules", "Custom ability priorities and conditional logic.", "›", page.phase14_rotation_advanced_panel)' not in source
