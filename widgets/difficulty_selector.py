# ==================================================
# Black Feather Foundry
#
# File:
# widgets/difficulty_selector.py
#
# Purpose:
# Standard difficulty selector used throughout
# the Foundry.
#
# ==================================================

from PySide6.QtWidgets import (
    QWidget,
    QRadioButton,
    QHBoxLayout,
)


class DifficultySelector(QWidget):
    """
    Standard Foundry difficulty selector.

    Allows selecting one of:
    - Normal
    - Veteran
    - Hardmode
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.normal = QRadioButton("Normal")
        self.veteran = QRadioButton("Veteran")
        self.hardmode = QRadioButton("Hardmode")

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addWidget(
            self.normal
        )

        layout.addWidget(
            self.veteran
        )

        layout.addWidget(
            self.hardmode
        )

        # layout.addStretch()

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def selected(self) -> str:
        """
        Returns the selected difficulty.
        """

        if self.normal.isChecked():
            return "Normal"

        if self.veteran.isChecked():
            return "Veteran"

        if self.hardmode.isChecked():
            return "Hardmode"

        return ""

    @property
    def text(self) -> str:
        """
        Returns the selected difficulty.
        """

        return self.selected

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def clear(self):

        self.normal.setChecked(False)
        self.veteran.setChecked(False)
        self.hardmode.setChecked(False)

    def set_selected(
        self,
        value: str,
    ):

        self.clear()

        if value == "Normal":
            self.normal.setChecked(True)

        elif value == "Veteran":
            self.veteran.setChecked(True)

        elif value == "Hardmode":
            self.hardmode.setChecked(True)

    def has_selection(self) -> bool:

        return bool(
            self.selected
        )