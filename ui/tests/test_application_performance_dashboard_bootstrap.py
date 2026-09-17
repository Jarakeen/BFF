from pathlib import Path


def test_build_editor_performance_no_longer_owns_dashboard_composition() -> None:
    source = Path("ui/build_editor_performance.py").read_text(encoding="utf-8")

    assert "install_performance_dashboard_polish()" not in source
    assert "install_performance_dashboard_timeline()" not in source
    assert "install_performance_dashboard_focus()" not in source
    assert "install_operations_console_focus()" not in source


def test_application_startup_owns_performance_dashboard_composition() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert (
        "from ui.application_performance_dashboard_bootstrap "
        "import bootstrap_performance_dashboard_extensions"
    ) in source
    assert source.index("install_build_workspace_tab_layout_fix()") < source.index(
        "bootstrap_performance_dashboard_extensions()"
    )
    assert source.index("bootstrap_performance_dashboard_extensions()") < source.index(
        "install_build_editor_performance()"
    )


def test_performance_dashboard_bootstrap_preserves_extension_order() -> None:
    source = Path("ui/application_performance_dashboard_bootstrap.py").read_text(
        encoding="utf-8"
    )

    ordered_calls = (
        "install_performance_healer_analysis_support()",
        "install_performance_dashboard_polish()",
        "install_performance_dashboard_overlay()",
        "install_performance_dashboard_timeline()",
        "install_performance_dashboard_immunity_compat()",
        "install_performance_dashboard_effect_retrieval()",
        "install_performance_dashboard_timeline_service()",
        "install_performance_dashboard_boss_activity()",
        "install_performance_dashboard_focus()",
        "install_performance_dashboard_healer_support()",
        "install_operations_console_focus()",
    )
    positions = [source.index(call) for call in ordered_calls]

    assert "def bootstrap_performance_dashboard_extensions()" in source
    assert positions == sorted(positions)
