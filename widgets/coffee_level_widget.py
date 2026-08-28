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

from engine.config import get_resource_path
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)


# COFFEELEVELS = [

#    "Trace",

#    "Detectable",

#    "Nominal",

#    "Operational",

#    "Elevated",

#    "High",

#    "Critical",

#    "Maximum",

#    "Experimental",

#    "Catastrophic",

#]


class CoffeeLevelWidget(QWidget):
    """
    Displays and randomizes the Foundry coffee level.
    """

    levelChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # --------------------------------------------------
        # State
        # --------------------------------------------------

        self._items = []
        self._generator = None

        # --------------------------------------------------
        # Widgets
        # --------------------------------------------------

        self.edit = QLineEdit()

        self.random_button = QPushButton()
        self.random_button.setToolTip(
            "Randomize value"
        )

        # --------------------------------------------------
        # Dice Icon
        # --------------------------------------------------

        icon_path = get_resource_path(
            "assets", "icons", "dice.svg"
        )

        if icon_path.exists():

            self.random_button.setIcon(
                QIcon(str(icon_path))
            )

        else:

            self.random_button.setText("🎲")

        # --------------------------------------------------
        # Layout
        # --------------------------------------------------

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(4)

        layout.addWidget(
            self.edit,
            1,
        )

        layout.addWidget(
            self.random_button,
        )

        # --------------------------------------------------
        # Signals
        # --------------------------------------------------

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

    def set_level(self, value):

        self.edit.setText(
            str(value)
        )


    def set_items(
        self,
        items,
    ):

        self._items = list(items)


    def set_generator(
        self,
        generator,
    ):

        self._generator = generator


    def clear(self):

        self.edit.clear()


    def randomize(self):

        #
        # Callback takes priority
        #

        if self._generator is not None:

            value = self._generator()

        #
        # Otherwise choose from supplied items
        #

        elif self._items:

            value = random.choice(
                self._items
            )

        #
        # Nothing configured
        #

        else:

            return

        self.set_level(value)