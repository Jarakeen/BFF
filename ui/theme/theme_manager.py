# ==================================================
# Black Feather Foundry
#
# File:
# ui/theme/theme_manager.py
#
# Purpose:
# Central theme manager.
#
# Responsible for:
#   - Colors
#   - Fonts
#   - Metrics
#   - Roles
#   - Theme assets
#   - QSS loading
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import (
    QFont,
    QIcon,
)

from PySide6.QtWidgets import QApplication

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ==================================================
# Theme
# ==================================================

class Theme:

    def __init__(
        self,
        name: str,
        folder: Path,
    ) -> None:

        self.name = name

        self.folder = folder

        #
        # Assets
        #

        self.logo = folder / "logo.ico"

        self.stylesheet = folder / "foundry.qss"

        self.preview = folder / "preview.png"

        self.background = folder / "background.png"

        #
        # Design System
        #

        self.colors = Colors

        self.fonts = Fonts

        self.metrics = Metrics

        self.roles = Roles


# ==================================================
# Default Theme
# ==================================================

def _default_theme() -> Theme:

    return Theme(

        name="Black Feather Foundry",

        folder=(
            PROJECT_ROOT
            / "assets"
            / "themes"
            / "bff"
        ),

    )


# ==================================================
# Theme Manager
# ==================================================

class ThemeManager:

    def __init__(
        self,
        theme: Theme | None = None,
    ):

        self._theme = theme or _default_theme()

    # -------------------------------------------------
    # Apply
    # -------------------------------------------------

    def apply(
        self,
        app: QApplication,
    ):

        #
        # Window Icon
        #

        if self.logo.exists():

            app.setWindowIcon(
                QIcon(str(self.logo))
            )

        #
        # Stylesheet
        #

        if self.stylesheet.exists():

            print("Loading:", self.stylesheet)
            print("Exists:", self.stylesheet.exists())

            app.setStyleSheet(

                self.stylesheet.read_text(
                    encoding="utf-8"
                )

            )

            print(
                f"Loaded theme '{self.name}'"
            )

        else:

            print(
                f"Missing stylesheet:\n{self.stylesheet}"
            )

    # -------------------------------------------------
    # Theme
    # -------------------------------------------------

    def set_theme(
        self,
        theme: Theme,
    ):

        self._theme = theme

    # -------------------------------------------------
    # Properties
    # -------------------------------------------------

    @property
    def name(self):

        return self._theme.name

    @property
    def logo(self):

        return self._theme.logo

    @property
    def stylesheet(self):

        return self._theme.stylesheet

    @property
    def preview(self):

        return self._theme.preview

    @property
    def background(self):

        return self._theme.background

    @property
    def colors(self):

        return self._theme.colors

    @property
    def fonts(self):

        return self._theme.fonts

    @property
    def metrics(self):

        return self._theme.metrics

    @property
    def roles(self):

        return self._theme.roles

    #
    # Compatibility aliases
    #

    @property
    def sidebar_color(self):

        return self.colors.SIDEBAR

    @property
    def paper_color(self):

        return self.colors.PAPER

    @property
    def accent_color(self):

        return self.colors.ACCENT

    @property
    def title_font(self):

        return self.fonts.title()

    @property
    def body_font(self):

        return self.fonts.body()