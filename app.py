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
    from ui.components.searchable_build_selectors import install as install_searchable_selectors

    # Install the shared skill/gear picker behavior before
    # importing pages that may construct BuildEditor widgets.
    install_searchable_selectors()

    from ui.main_window import MainWindow

    #
    # Theme
    #

    theme = ThemeManager()
    app_icon = get_resource_path("bff.ico")

    if theme.logo and app_icon.exists():
        app.setWindowIcon(
            QIcon(str(app_icon))
        )

    style_file = get_resource_path(
        "assets", "themes", "bff", "foundry.qss"
    )

    if style_file.exists():

        app.setStyleSheet(
            style_file.read_text(
                encoding="utf-8"
            )
        )

    #
    # Main Window
    #

    window = MainWindow()

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())