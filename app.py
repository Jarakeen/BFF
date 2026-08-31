from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from engine.config import get_resource_path


def _set_windows_app_id() -> None:
    """
    Set the Windows AppUserModelID so the taskbar icon
    uses the Foundry branding instead of python.exe.
    """

    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "BlackFeatherFoundry.FieldOffice"
        )

    except Exception:
        pass


def main() -> int:

    _set_windows_app_id()

    # Create the Qt application FIRST.
    app = QApplication(sys.argv)

    app.setApplicationName("Black Feather Foundry Field Office")
    app.setOrganizationName("Black Feather Foundry")

    # Set the application icon as early as possible so Windows does not briefly
    # fall back to the generic Python/Qt icon during startup.
    app_icon = get_resource_path("bff.ico")
    if app_icon.exists():
        app.setWindowIcon(QIcon(str(app_icon)))

    # Show one static, motion-free startup screen before loading the heavier UI
    # modules. The splash does not animate, blink, fade, or cycle text.
    from ui.startup_splash import create_startup_splash

    splash = create_startup_splash()
    splash.show()
    app.processEvents()

    # Import Qt-dependent modules AFTER QApplication exists.
    from ui.theme import ThemeManager
    from ui.grimoire_theme import apply_grimoire_theme
    from ui.components.searchable_build_selectors import install as install_searchable_selectors
    from ui.scribing_support import install as install_scribing_support
    from ui.scribing_editor_compat import install as install_scribing_editor_compat

    install_searchable_selectors()
    install_scribing_support()
    install_scribing_editor_compat()

    from ui.main_window import MainWindow

    theme = ThemeManager()

    # Grimoire is the current BFF visual skin. Keep the existing foundry.qss
    # as a safe fallback so a missing packaged texture cannot prevent startup.
    if not apply_grimoire_theme(app):
        style_file = get_resource_path("assets", "themes", "bff", "foundry.qss")
        if style_file.exists():
            app.setStyleSheet(style_file.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    app.processEvents()
    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
