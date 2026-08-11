# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_metric.py
#
# Purpose:
# Generic label + large value display.
#
# Covers the encounter timer, "CP 2210", "19/19",
# sidebar stats ("Pulls: 0") -- one component at a few
# sizes, not a widget per use.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.theme.colors import Colors
from ui.theme.fonts import Fonts


class FoundryMetric(QWidget):
    """
    A label above (or below) a large value.

        FoundryMetric("PULLS", "37")
        FoundryMetric("ENCOUNTER TIMER", "00:00", size=28)
    """

    def __init__(
        self,
        label: str,
        value: str = "",
        *,
        unit: str = "",
        size: int = 18,
        color: str = Colors.TEXT,
        label_first: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryMetric",
            True,
        )

        self.label = QLabel(
            label.upper()
        )

        self.label.setProperty(
            "metricLabel",
            True,
        )

        self.value = QLabel()

        self.value.setProperty(
            "metricValue",
            True,
        )

        self._unit = unit

        self._size = size

        self._color = color

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(2)

        widgets = (
            [self.label, self.value]
            if label_first
            else [self.value, self.label]
        )

        for w in widgets:
            layout.addWidget(w)

        self.set_value(value)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_value(
        self,
        value: str,
    ):

        text = f"{value}{self._unit}" if value != "" else "--"

        self.value.setText(text)

        font = Fonts.metric()

        font.setPointSize(self._size)

        self.value.setFont(font)

        self.value.setStyleSheet(
            f"color: {self._color};"
        )

    def set_label(
        self,
        label: str,
    ):

        self.label.setText(
            label.upper()
        )
