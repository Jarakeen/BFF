from pathlib import Path


def test_help_surfaces_use_native_main_window_registration() -> None:
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")
    support = Path("ui/help_support.py").read_text(encoding="utf-8")

    assert "install_help_surfaces(self)" in main_window
    assert "_install_settings_help(window)" in support
    assert "_add_context_help_buttons(window)" in support
    assert "MainWindow.build_ui =" not in support
    assert "from ui.main_window import MainWindow" not in support


def test_help_topic_extensions_still_install_before_main_window_construction() -> None:
    app = Path("app.py").read_text(encoding="utf-8")
    support = Path("ui/help_support.py").read_text(encoding="utf-8")

    assert "install_help_feature_extensions()" in support
    assert app.index("install_help_support()") < app.index(
        "from ui.main_window import MainWindow"
    )
