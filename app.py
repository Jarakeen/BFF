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


def _set_native_windows_icon(window, icon_path: Path) -> None:
    """Force the Win32 top-level window icon used by Alt-Tab/taskbar surfaces."""
    if sys.platform != "win32" or not icon_path.is_file():
        return

    try:
        import ctypes

        user32 = ctypes.windll.user32

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        icon_handle = user32.LoadImageW(
            None,
            str(icon_path),
            IMAGE_ICON,
            0,
            0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        if not icon_handle:
            return

        hwnd = int(window.winId())
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_handle)
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon_handle)
    except Exception:
        # Qt's normal icon path remains the fallback on nonstandard Windows
        # environments or if the native call is unavailable.
        pass


def main() -> int:

    _set_windows_app_id()

    app = QApplication(sys.argv)

    app.setApplicationName("Black Feather Foundry Field Office")
    app.setOrganizationName("Black Feather Foundry")

    app_icon = get_resource_path("bff.ico")
    foundry_icon = QIcon(str(app_icon)) if app_icon.exists() else QIcon()
    if not foundry_icon.isNull():
        app.setWindowIcon(foundry_icon)

    from ui.startup_splash import create_startup_splash

    splash = create_startup_splash()
    splash.show()
    app.processEvents()

    from ui.theme import ThemeManager
    from ui.grimoire_theme import apply_grimoire_theme
    from ui.components.searchable_build_selectors import install as install_searchable_selectors
    from ui.scribing_support import install as install_scribing_support
    from ui.scribing_editor_compat import install as install_scribing_editor_compat
    from ui.phase5_build_ui_support import install as install_phase5_build_ui_support
    from ui.phase5_operations_progression_support import install as install_phase5_operations_progression_support
    from ui.phase5_potion_picker_support import install as install_phase5_potion_picker_support

    install_searchable_selectors()
    install_scribing_support()
    install_scribing_editor_compat()
    install_phase5_build_ui_support()
    install_phase5_operations_progression_support()
    install_phase5_potion_picker_support()

    from ui.main_window import MainWindow

    theme = ThemeManager()

    if not apply_grimoire_theme(app):
        style_file = get_resource_path("assets", "themes", "bff", "foundry.qss")
        if style_file.exists():
            app.setStyleSheet(style_file.read_text(encoding="utf-8"))

    window = MainWindow()
    if not foundry_icon.isNull():
        window.setWindowIcon(foundry_icon)
    window.show()
    app.processEvents()

    _set_native_windows_icon(window, app_icon)

    splash.finish(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
