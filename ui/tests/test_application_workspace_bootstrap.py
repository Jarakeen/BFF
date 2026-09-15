from pathlib import Path


def test_schedule_feature_no_longer_owns_workspace_composition() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert "bootstrap_workspace_extensions" not in source
    assert "install_roster_import_support()" not in source
    assert "install_rotation_dashboard_layout_support()" not in source
    assert "install_build_context_variant_support()" not in source


def test_application_startup_owns_workspace_composition_before_schedule_feature() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert "from ui.application_workspace_bootstrap import bootstrap_workspace_extensions" in source
    assert source.index("bootstrap_workspace_extensions()") < source.index(
        "install_operations_console_schedule_support()"
    )


def test_workspace_bootstrap_owns_cross_feature_install_order() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert "def bootstrap_workspace_extensions()" in source
    assert "install_roster_import_support()" in source
    assert "install_rotation_dashboard_layout_support()" not in source
    assert "install_build_rotation_artifact_support()" in source
    assert "install_build_context_variant_support()" in source
    assert source.index("install_roster_assignment_persistence_support()") < source.index(
        "install_roster_assignment_action_support()"
    )


def test_startup_order_tests_no_longer_treat_schedule_feature_as_bootstrap() -> None:
    legacy = 'Path("ui/operations_console_schedule_support.py")'
    offenders = []
    for path in Path("ui/tests").glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue
        if legacy in path.read_text(encoding="utf-8"):
            offenders.append(path.as_posix())

    assert offenders == []
