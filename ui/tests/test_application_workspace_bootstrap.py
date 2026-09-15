from pathlib import Path


def test_schedule_feature_no_longer_owns_workspace_composition() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "bootstrap_workspace_extensions()" in source
    assert "install_roster_import_support()" not in source
    assert "install_rotation_dashboard_layout_support()" not in source
    assert "install_build_context_variant_support()" not in source


def test_workspace_bootstrap_owns_cross_feature_install_order() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "def bootstrap_workspace_extensions()" in source
    assert "install_roster_import_support()" in source
    assert "install_rotation_dashboard_layout_support()" in source
    assert "install_build_context_variant_support()" in source
    assert source.index("install_rotation_dashboard_layout_support()") < source.index(
        "install_build_rotation_artifact_support()"
    )
    assert source.index("install_roster_assignment_persistence_support()") < source.index(
        "install_roster_assignment_action_support()"
    )
