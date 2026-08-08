# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_progress_bar.py
#
# Purpose:
# Standard progress indicator used throughout the
# Foundry.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import QProgressBar

from ui.theme.fonts import Fonts


class FoundryProgressBar(QProgressBar):
    """
    Standard Foundry progress bar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setProperty(
            "foundryProgress",
            True,
        )

        self.setFont(
            Fonts.metric()
        )

        self.setRange(
            0,
            100,
        )

        self.setValue(0)

        self.setTextVisible(True)

        self.setFormat("%p%")

        self.setMinimumHeight(24)

    # --------------------------------------------------
    # Convenience
    # --------------------------------------------------

    def set_percentage(
        self,
        value: int,
    ):

        value = max(
            0,
            min(
                100,
                value,
            ),
        )

        self.setValue(value)

    def reset(self):

        self.setValue(0)    