# ==================================================
# Black Feather Foundry
#
# File:
# ui/components/foundry_table.py
#
# Purpose:
# Generic, data-driven table.
#
# Takes plain columns + rows; it has no idea what a
# "boss ability" or "raid assignment" is. A cell value
# is either a string, or a small dict describing how to
# render it (badge, icon+text), so callers can express
# severity/role coloring without the table knowing what
# those mean.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ui.components.foundry_icon import FoundryIcon
from ui.components.foundry_status_badge import FoundryStatusBadge
from ui.theme.fonts import Fonts
from ui.theme.metrics import Metrics


class FoundryTable(QTableWidget):
    """
    A generic striped, header-styled table.

        FoundryTable(
            columns=["Ability", "Type", "Damage"],
            rows=[
                ["Twilight Volley", "Direct Damage",
                 {"badge": "Medium", "scale": "severity", "key": "medium"}],
                ...
            ],
        )

    A cell value can be:
      - a plain string
      - {"badge": text, "scale": ..., "key": ...} / {"badge": text, "color": ...}
      - {"icon": icon_name, "text": text, "color": color}
    """

    def __init__(
        self,
        columns: list[str] | None = None,
        rows: list[list] | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setProperty(
            "foundryTable",
            True,
        )

        self.setFont(
            Fonts.table()
        )

        self.setAlternatingRowColors(True)

        self.setShowGrid(False)

        self.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.verticalHeader().setVisible(False)

        self.verticalHeader().setDefaultSectionSize(
            Metrics.TABLE_ROW
        )

        self.horizontalHeader().setMinimumSectionSize(60)

        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.horizontalHeader().setFixedHeight(
            Metrics.TABLE_HEADER
        )

        if columns is not None:
            self.set_data(columns, rows or [])

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def set_data(
        self,
        columns: list[str],
        rows: list[list],
    ):

        self.setColumnCount(len(columns))

        self.setHorizontalHeaderLabels(columns)

        self.setRowCount(len(rows))

        for r, row in enumerate(rows):

            for c, value in enumerate(row):

                self._set_cell(r, c, value)

    # --------------------------------------------------
    # Cell rendering
    # --------------------------------------------------

    def _set_cell(
        self,
        row: int,
        col: int,
        value,
    ):

        if isinstance(value, dict) and "badge" in value:

            badge = FoundryStatusBadge(
                value["badge"],
                scale=value.get("scale"),
                key=value.get("key"),
                color=value.get("color"),
            )

            self._set_cell_widget(row, col, [badge])

            return

        if isinstance(value, dict) and "icon" in value:

            icon = FoundryIcon(
                value["icon"],
                size=Metrics.ICON_SMALL,
                color=value.get("color", "#9AA3A9"),
            )

            text = QTableWidgetItem(
                value.get("text", "")
            )

            self._set_cell_widget(
                row, col, [icon], trailing_item=text
            )

            return

        item = QTableWidgetItem(str(value))

        self.setItem(row, col, item)

    def _set_cell_widget(
        self,
        row: int,
        col: int,
        widgets: list,
        trailing_item: QTableWidgetItem | None = None,
    ):

        container = QWidget()

        layout = QHBoxLayout(container)

        layout.setContentsMargins(10, 2, 10, 2)

        layout.setSpacing(6)

        for w in widgets:
            layout.addWidget(w)

        if trailing_item is not None:

            from PySide6.QtWidgets import QLabel

            label = QLabel(trailing_item.text())

            layout.addWidget(label)

        layout.addStretch()

        self.setCellWidget(row, col, container)
