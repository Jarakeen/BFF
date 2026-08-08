# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_button.py
#
# Purpose:
# Standard button used throughout the Foundry.
#
# ==================================================

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton

from ui.theme.fonts import Fonts


class ButtonRole(Enum):
    PRIMARY = auto()
    SECONDARY = auto()
    SUCCESS = auto()
    WARNING = auto()
    DANGER = auto()
    GHOST = auto()


class FoundryButton(QPushButton):
    """
    Standard Foundry button.

    Provides consistent typography, sizing and
    semantic styling through dynamic properties.
    """

    def __init__(
        self,
        text: str = "",
        *,
        icon: QIcon | None = None,
        role: ButtonRole = ButtonRole.SECONDARY,
        parent=None,
    ):
        super().__init__(text, parent)

        self.setFont(
            Fonts.button()
        )

        self.setMinimumHeight(38)

        if icon is not None:
            self.setIcon(icon)

        self.setRole(role)

    # --------------------------------------------------
    # Theme
    # --------------------------------------------------

    def setRole(
        self,
        role: ButtonRole,
    ):

        #
        # Remove old role properties
        #

        for name in (
            "primary",
            "secondary",
            "success",
            "warning",
            "danger",
            "ghost",
        ):
            self.setProperty(name, False)

        #
        # Apply new role
        #

        match role:

            case ButtonRole.PRIMARY:
                self.setProperty("primary", True)

            case ButtonRole.SECONDARY:
                self.setProperty("secondary", True)

            case ButtonRole.SUCCESS:
                self.setProperty("success", True)

            case ButtonRole.WARNING:
                self.setProperty("warning", True)

            case ButtonRole.DANGER:
                self.setProperty("danger", True)

            case ButtonRole.GHOST:
                self.setProperty("ghost", True)

        #
        # Refresh stylesheet
        #

        self.style().unpolish(self)
        self.style().polish(self)