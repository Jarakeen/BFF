# widgets/coffee_selector.py

from __future__ import annotations

from PySide6.QtWidgets import QComboBox

COFFEE_OPTIONS = [
    "Unavailable",
    "Requested",
    "Brewing",
    "Operational",
    "Enhanced",
    "Maximum",
    "Experimental",
]


class CoffeeSelector(QComboBox):
    """
    Standard Black Feather Foundry coffee selector.

    Used anywhere the UI needs to select
    the current coffee status.
    """

    SOURCE_MAP = {
        "Unavailable": "Unavailable",
        "Requested": "Requested",
        "Brewing": "Brewing",
        "Operational": "Operational",
        "Enhanced": "Enhanced",
        "Maximum": "Maximum",
        "Experimental": "Experimental",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.addItems(COFFEE_OPTIONS)

    @property
    def source_name(self) -> str:
        """
        Returns the OBS source name.
        """
        return self.SOURCE_MAP[self.currentText()]

    def set_source(self, source: str) -> None:
            """
            Sets the selector from an OBS source name.
            """
            for label, obs_source in self.SOURCE_MAP.items():
                if obs_source == source:
                    self.setCurrentText(label)
                    return

    def reset(self) -> None:
            """
            Reset to the default coffee state.
            """
            self.setCurrentIndex(0)        


coffee = CoffeeSelector()

coffee.source_name      # OBS source name
coffee.set_source(...)  # Load from saved data
coffee.reset()          # Default state        