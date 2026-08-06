# ==================================================
# Black Feather Foundry
#
# File:
# widgets/achievement_checklist.py
#
# Purpose:
# Tracks the achievements for the current run.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
)


class AchievementChecklist(QWidget):
    """
    Editable checklist for the current Achievement Run.
    """

    ROWS = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget(
            self.ROWS,
            3,
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Achievement",
                "In Progress",
                "Complete",
            ]
        )

        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )

        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self.table.setAlternatingRowColors(True)

        #
        # Populate rows
        #

        for row in range(self.ROWS):

            item = QTableWidgetItem()

            self.table.setItem(
                row,
                0,
                item,
            )

            progress = QCheckBox()

            complete = QCheckBox()

            progress.setStyleSheet(
                "margin-left:auto; margin-right:auto;"
            )

            complete.setStyleSheet(
                "margin-left:auto; margin-right:auto;"
            )

            self.table.setCellWidget(
                row,
                1,
                progress,
            )

            self.table.setCellWidget(
                row,
                2,
                complete,
            )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addWidget(
            self.table
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def clear(self):
        """
        Clear every achievement.
        """

        for row in range(self.ROWS):

            self.table.item(
                row,
                0,
            ).setText("")

            self.table.cellWidget(
                row,
                1,
            ).setChecked(False)

            self.table.cellWidget(
                row,
                2,
            ).setChecked(False)

    def achievements(self) -> list[dict]:
        """
        Return the current checklist.
        """

        data = []

        for row in range(self.ROWS):

            data.append(
                {
                    "achievement": self.table.item(
                        row,
                        0,
                    ).text(),

                    "progress": self.table.cellWidget(
                        row,
                        1,
                    ).isChecked(),

                    "complete": self.table.cellWidget(
                        row,
                        2,
                    ).isChecked(),
                }
            )

        return data