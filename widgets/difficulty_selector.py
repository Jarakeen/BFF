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
    QCheckBox,
    QHBoxLayout,
)


class DifficultySelector(QWidget):
    """
    Standard Foundry difficulty selector.

    Allows selecting any combination of:
    - Normal
    - Veteran
    - Hardmode
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.normal = QCheckBox("Normal")
        self.veteran = QCheckBox("Veteran")
        self.hardmode = QCheckBox("Hardmode")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.normal)
        layout.addWidget(self.veteran)
        layout.addWidget(self.hardmode)
        # layout.addStretch()

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def selected(self) -> list[str]:
        """
        Returns the selected difficulties.
        """

        values = []

        if self.normal.isChecked():
            values.append("Normal")

        if self.veteran.isChecked():
            values.append("Veteran")

        if self.hardmode.isChecked():
            values.append("Hardmode")

        return values

    @property
    def text(self) -> str:
        """
        Returns a comma-separated string.
        """

        return ", ".join(self.selected)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def clear(self):

        self.normal.setChecked(False)
        self.veteran.setChecked(False)
        self.hardmode.setChecked(False)

    def set_selected(self, values: list[str]):

        self.clear()

        self.normal.setChecked(
            "Normal" in values
        )

        self.veteran.setChecked(
            "Veteran" in values
        )

        self.hardmode.setChecked(
            "Hardmode" in values
        )

    def has_selection(self) -> bool:

        return bool(self.selected)