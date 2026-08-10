# ui/theme/__init__.py

from .colors import Colors
from .fonts import Fonts
from .metrics import Metrics
from .roles import Roles
from .theme_manager import Theme, ThemeManager
__all__ = ["Colors", "Fonts", "Metrics", "Roles", "Theme", "ThemeManager"]


def __init__(self) -> None:
    super().__init__()

    self.setStyleSheet(
        FOUNDRY_THEME
    )

    self.setWindowTitle(
        "Black Feather Foundry Field Office"
    )

    self.resize(
        1500,
        950,
    )

    self.setMinimumSize(
        1200,
        800,
    )