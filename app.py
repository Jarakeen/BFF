from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


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

    #
    # Create the Qt application FIRST
    #

    app = QApplication(sys.argv)

    app.setApplicationName(
        "Black Feather Foundry Field Office"
    )

    app.setOrganizationName(
        "Black Feather Foundry"
    )

    #
    # Import Qt-dependent modules AFTER QApplication exists.
    # This helps us catch modules that accidentally create
    # widgets during import.
    #

    from ui.theme import ThemeManager
    from ui.main_window import MainWindow

    #
    # Theme
    #

    theme = ThemeManager()

    theme.apply(app)

    #
    # Main Window
    #

    window = MainWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())