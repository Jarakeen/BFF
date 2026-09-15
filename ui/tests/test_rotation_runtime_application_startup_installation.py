from pathlib import Path


def test_runtime_application_is_native_to_canonical_rotation_construction() -> None:
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )
    support = Path("ui/rotation_runtime_application_support.py").read_text(
        encoding="utf-8"
    )
    bootstrap = Path("ui/application_workspace_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "install_rotation_runtime_application(self)" in dashboard
    assert "CanonicalRotationDashboardPage.__init__ =" not in support
    assert "install_rotation_runtime_application_support()" not in bootstrap


def test_runtime_application_coexists_with_native_rotation_build_refresh() -> None:
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )

    assert "install_rotation_runtime_application(self)" in dashboard
    assert "def showEvent(self, event)" in dashboard
    assert "self._refresh_saved_builds()" in dashboard
