# ==================================================
# Black Feather Foundry
#
# File:
# widgets/overlay_controls.py
#
# Purpose:
# Controls for the OBS overlay.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QPushButton,
)

from widgets.weather_selector import WeatherSelector
from widgets.coffee_selector import CoffeeSelector
from widgets.coffee_level_widget import CoffeeLevelWidget


class OverlayControls(QWidget):
    """
    Controls for the live OBS overlay.
    """

    pushRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.weather = WeatherSelector()

        self.coffee = CoffeeSelector()

        self.coffeeLevel = CoffeeLevelWidget()

        self.push_button = QPushButton(
            "Push Overlay"
        )

        #
        # Layout
        #

        layout = QFormLayout(self)

        layout.addRow(
            "Weather",
            self.weather,
        )

        layout.addRow(
            "Coffee",
            self.coffee,
        )

        layout.addRow(
            "Coffee Level",
            self.coffeeLevel,
        )

        layout.addRow(
            "",
            self.push_button,
        )

        #
        # Signals
        #

        self.push_button.clicked.connect(
            self.pushRequested.emit
        )

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def model(self) -> dict:
        """
        Return the current overlay settings.
        """

        return {
            "weather": self.weather.obs_source,
            "coffee": self.coffee.source_name,
            "coffeeLevel": self.coffeeLevel.value,
        }

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Reset the overlay controls.
        """

        self.weather.reset()

        self.coffee.reset()

        self.coffeeLevel.reset()