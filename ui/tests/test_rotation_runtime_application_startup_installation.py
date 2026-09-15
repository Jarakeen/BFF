from pathlib import Path


def test_runtime_application_support_is_installed_at_app_startup() -> None:
    source = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")

    assert (
        "from ui.rotation_runtime_application_support import install as "
        "install_rotation_runtime_application_support"
    ) in source
    assert "install_rotation_runtime_application_support()" in source


def test_runtime_application_coexists_with_native_rotation_build_refresh() -> None:
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )

    assert "install_rotation_runtime_application_support()" in bootstrap
    assert "rotation_navigation_refresh_support" not in bootstrap
    assert "def showEvent(self, event)" in dashboard
    assert "self._refresh_saved_builds()" in dashboard
