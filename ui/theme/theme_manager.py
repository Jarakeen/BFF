# ui/theme/theme_manager.py
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Theme:
    """
    Defines a complete visual theme.

    A Theme bundles together:
      - Colors
      - Fonts
      - Metrics
      - Roles (QSS selector-name constants)
      - Images / Logos

    Widgets should ask ThemeManager for these values instead of hardcoding
    them throughout the application.
    """

    def __init__(
        self,
        name: str,
        logo: str | None,
        background_image: str | None,
    ) -> None:

        self.name = name

        # Images
        self.logo = logo
        self.background_image = background_image

        # Colors
        self.colors = Colors

        # Fonts
        self.fonts = Fonts

        # Metrics
        self.metrics = Metrics

        # Roles
        self.roles = Roles


def _default_theme() -> Theme:
    logo_path = PROJECT_ROOT / "Otter_Engineer.ico"

    return Theme(
        name="Black Feather Foundry",
        logo=str(logo_path) if logo_path.exists() else None,
        # No background art shipped with the project yet - stays None until
        # one is added, rather than pointing at a file that doesn't exist.
        background_image=None,
    )


class ThemeManager:
    """
    Single source of truth for the application's appearance.

    Example:

        theme = ThemeManager()

        theme.colors.ACCENT
        theme.colors.CARD

        theme.fonts.title()
        theme.fonts.button()

        theme.metrics.BUTTON_HEIGHT
        theme.metrics.PAGE_MARGIN

        theme.roles.CARD
        theme.roles.NAV
    """

    def __init__(self, theme: Theme | None = None) -> None:
        self._theme = theme or _default_theme()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme

    # -------------------------------------------------
    # Theme
    # -------------------------------------------------

    @property
    def name(self) -> str:
        return self._theme.name

    # -------------------------------------------------
    # Images
    # -------------------------------------------------

    @property
    def logo(self) -> str | None:
        return self._theme.logo

    @property
    def background_image(self) -> str | None:
        return self._theme.background_image

    # -------------------------------------------------
    # Design System
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Convenience Aliases
    # (keeps older code working)
    # -------------------------------------------------

    @property
    def sidebar_color(self) -> str:
        return self.colors.SIDEBAR

    @property
    def paper_color(self) -> str:
        return self.colors.PAPER

    @property
    def accent_color(self) -> str:
        return self.colors.ACCENT

    @property
    def title_font(self) -> QFont:
        return self.fonts.title()

    @property
    def body_font(self) -> QFont:
        return self.fonts.body()
