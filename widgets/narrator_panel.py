# ==================================================
# Black Feather Foundry
#
# File:
# widgets/narrator_panel.py
#
# Purpose:
# Quick-access controls for posting narrator
# observations during a live Expedition.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QPushButton,
)

from services.narrator_service import NarratorService


class NarratorPanel(QWidget):
    """
    Displays narrator categories and emits the
    selected category when clicked.
    """

    narratorRequested = Signal(str)

    def __init__(
        self,
        narrator_service: NarratorService,
        parent=None,
    ):
        super().__init__(parent)

        self.narrator_service = narrator_service

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        layout = QGridLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        columns = 4

        categories = self.narrator_service.categories()

        print("Building buttons for:", categories)

        narrator_buttons = [
            ("General Observations", "General"),
            ("Healers", "Healers"),
            ("Tanks", "Tanks"),
            ("DPS", "DPS"),
            ("Funny Moments", "FunnyMoments"),
            ("Progression", "Progression"),
        ]

        columns = 2

        for index, (text, category) in enumerate(narrator_buttons):

            button = QPushButton(text)

            button.clicked.connect(
                lambda checked=False, c=category:
                    self.narratorRequested.emit(c)
            )

            row = index // columns
            column = index % columns

            layout.addWidget(
                button,
                row,
                column,
            )