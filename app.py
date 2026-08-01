from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import ThemeManager


def _set_windows_app_id() -> None:
    """On Windows, taskbar icon grouping is keyed off the process's AppUserModelID
    rather than the window icon alone. Without this, Windows shows the generic
    python.exe icon on the taskbar even though the window icon looks right."""
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

    app = QApplication(sys.argv)
    app.setApplicationName("Black Feather Foundry Field Office")
    app.setOrganizationName("Black Feather Foundry")

    theme = ThemeManager()
    if theme.logo:
        app.setWindowIcon(QIcon(theme.logo))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
