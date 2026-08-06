# ==================================================
# Black Feather Foundry
#
# File:
# widgets/achievement_table.py
#
# Purpose:
# Displays achievement runs in a reusable table.
#
# ==================================================

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)


class AchievementTable(QTableWidget):
    """
    Standard table for displaying achievement runs.
    """

    HEADERS = [
        "Achievement",
        "Trial",
        "Progress",
        "Status",
        "Leader",
        "Date",
    ]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)

        self.setHorizontalHeaderLabels(self.HEADERS)

        self.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        self.setAlternatingRowColors(True)

        self.setSortingEnabled(True)

        self.verticalHeader().setVisible(False)

        self.horizontalHeader().setStretchLastSection(True)

        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

    # --------------------------------------------------
    # Data
    # --------------------------------------------------

    def clear_table(self):
        self.setRowCount(0)

    def add_run(
        self,
        achievement: str,
        trial: str,
        progress: str,
        status: str,
        leader: str,
        date: str,
    ):

        row = self.rowCount()

        self.insertRow(row)

        values = [
            achievement,
            trial,
            progress,
            status,
            leader,
            date,
        ]

        for column, value in enumerate(values):

            item = QTableWidgetItem(str(value))

            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )

            self.setItem(
                row,
                column,
                item,
            )

    def load_runs(self, runs):

        self.clear_table()

        for run in runs:

            self.add_run(
                achievement=run.achievement,
                trial=run.trial,
                progress=run.progress,
                status=run.status,
                leader=run.leader,
                date=run.date,
            )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def selected_row(self):

        rows = self.selectionModel().selectedRows()

        if not rows:
            return None

        return rows[0].row()