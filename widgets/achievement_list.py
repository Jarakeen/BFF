# ==================================================
# Black Feather Foundry
#
# File:
# widgets/achievement_list.py
#
# Purpose:
# Editable list of achievements for the
# current Achievement Run.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QVBoxLayout,
)


class AchievementList(QWidget):
    """
    Editable list of achievements for the
    current run.
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
        # Create rows
        #

        for row in range(self.ROWS):

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(),
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
        Reset the list.
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

    @property
    def achievements(self) -> list[dict]:
        """
        Return the current achievement list.
        """

        items = []

        for row in range(self.ROWS):

            items.append(
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

        return items