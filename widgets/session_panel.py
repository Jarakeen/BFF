# ==================================================
# Black Feather Foundry
#
# File:
# widgets/session_panel.py
#
# Purpose:
# Displays the current Expedition session.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLabel,
    QLineEdit,
)


class SessionPanel(QWidget):
    """
    Displays the current Expedition session.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.current_boss = QLineEdit()

        self.elapsed_time = QLabel("00:00:00")

        self.total_pulls = QLabel("0")

        self.boss_pulls = QLabel("0")

        self.boss_wipes = QLabel("0")

        self.best_pull = QLabel("--")

        #
        # Layout
        #

        layout = QFormLayout(self)

        layout.addRow(
            "Current Boss",
            self.current_boss,
        )

        layout.addRow(
            "Elapsed Time",
            self.elapsed_time,
        )

        layout.addRow(
            "Total Pulls",
            self.total_pulls,
        )

        layout.addRow(
            "Boss Pulls",
            self.boss_pulls,
        )

        layout.addRow(
            "Boss Wipes",
            self.boss_wipes,
        )

        layout.addRow(
            "Best Pull",
            self.best_pull,
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def set_elapsed_time(
        self,
        text: str,
    ):

        self.elapsed_time.setText(text)

    def set_total_pulls(
        self,
        value: int,
    ):

        self.total_pulls.setText(str(value))

    def set_boss_pulls(
        self,
        value: int,
    ):

        self.boss_pulls.setText(str(value))

    def set_boss_wipes(
        self,
        value: int,
    ):

        self.boss_wipes.setText(str(value))

    def set_best_pull(
        self,
        value: int | None,
    ):

        if value is None:
            self.best_pull.setText("--")
        else:
            self.best_pull.setText(f"{value}%")

    def clear(self):
        """
        Reset the panel.
        """

        self.current_boss.clear()

        self.elapsed_time.setText("00:00:00")

        self.total_pulls.setText("0")

        self.boss_pulls.setText("0")

        self.boss_wipes.setText("0")

        self.best_pull.setText("--")