from pathlib import Path


def test_runtime_application_support_is_installed_at_app_startup() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    assert (
        "from ui.rotation_runtime_application_support import install as "
        "install_rotation_runtime_application_support"
    ) in source
    assert "install_rotation_runtime_application_support()" in source


def test_runtime_application_installs_after_rotation_build_refresh_support() -> None:
    source = Path("ui/operations_console_schedule_support.py").read_text(encoding="utf-8")

    refresh_call = source.index("install_rotation_navigation_refresh_support()")
    runtime_call = source.index("install_rotation_runtime_application_support()")

    assert refresh_call < runtime_call
