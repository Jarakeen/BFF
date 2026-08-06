# ==================================================
# Black Feather Foundry
#
# File:
# widgets/coffee_level_widget.py
#
# Purpose:
# Coffee level selector with Foundry randomizer.
#
# ==================================================

from pathlib import Path
import random

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)


COFFEE_LEVELS = [

    "Trace",

    "Detectable",

    "Nominal",

    "Operational",

    "Elevated",

    "High",

    "Critical",

    "Maximum",

    "Experimental",

    "Catastrophic",

]


class CoffeeLevelWidget(QWidget):
    """
    Displays and randomizes the Foundry coffee level.
    """

    levelChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Widgets
        #

        self.edit = QLineEdit()

        self.random_button = QPushButton()

        self.random_button.setToolTip(
            "Randomize coffee level"
        )

        #
        # Dice icon
        #

        icon_path = (
            Path("assets")
            / "icons"
            / "dice.svg"
        )

        if icon_path.exists():

            self.random_button.setIcon(
                QIcon(str(icon_path))
            )

        else:

            self.random_button.setText("🎲")

        self.random_button.setFixedWidth(34)

        #
        # Layout
        #

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(4)

        layout.addWidget(self.edit)

        layout.addWidget(self.random_button)

        #
        # Signals
        #

        self.edit.textChanged.connect(
            self.levelChanged.emit
        )

        self.random_button.clicked.connect(
            self.randomize
        )

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def level(self) -> str:
        return self.edit.text().strip()

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_level(self, level: str):

        self.edit.setText(level)

    def clear(self):

        self.edit.clear()

    def randomize(self):

        self.set_level(
            random.choice(COFFEE_LEVELS)
        )