# ==================================================
# Black Feather Foundry
#
# File:
# widgets/raid_controls.py
#
# Purpose:
# Controls for recording raid progression.
#
# ==================================================

from __future__ import annotations

from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QPushButton,
    QSpinBox,
)


class RaidControls(QWidget):
    """
    Controls used during a live raid.
    """

    pullStarted = Signal()
    ultPullStarted = Signal()
    wipeRecorded = Signal(int, bool)
    bossCleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Controls
        #

        self.first_pull = QCheckBox(
            "First pull on this boss"
        )

        self.pull_button = QPushButton(
            "Pull Started"
        )

        self.ult_pull_button = QPushButton(
            "Ult Pull"
        )

        self.wipe_percent = QSpinBox()

        self.wipe_percent.setRange(0, 100)
        self.wipe_percent.setSuffix("%")

        self.rough_night = QCheckBox(
            "Rough night (skip narrator)"
        )

        self.wipe_button = QPushButton(
            "Record Wipe"
        )

        self.clear_button = QPushButton(
            "Boss Clear"
        )

        #
        # Layout
        #

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.first_pull
        )

        pull_row = QHBoxLayout()

        pull_row.addWidget(
            self.pull_button
        )

        pull_row.addWidget(
            self.ult_pull_button
        )

        layout.addLayout(
            pull_row
        )

        form = QFormLayout()

        form.addRow(
            "Reached",
            self.wipe_percent,
        )

        layout.addLayout(
            form
        )

        layout.addWidget(
            self.rough_night
        )

        layout.addWidget(
            self.wipe_button
        )

        # layout.addStretch()

        layout.addWidget(
            self.clear_button
        )

        #
        # Signals
        #

        self.pull_button.clicked.connect(
            self.pullStarted.emit
        )

        self.ult_pull_button.clicked.connect(
            self.ultPullStarted.emit
        )

        self.wipe_button.clicked.connect(
            self._emit_wipe
        )

        self.clear_button.clicked.connect(
            self.bossCleared.emit
        )

    # --------------------------------------------------
    # Properties
    # --------------------------------------------------

    @property
    def is_first_pull(self) -> bool:
        return self.first_pull.isChecked()

    @property
    def wipe_percentage(self) -> int:
        return self.wipe_percent.value()

    @property
    def is_rough_night(self) -> bool:
        return self.rough_night.isChecked()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _emit_wipe(self):

        self.wipeRecorded.emit(
            self.wipe_percentage,
            self.is_rough_night,
        )

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Reset the controls.
        """

        self.first_pull.setChecked(False)

        self.wipe_percent.setValue(0)

        self.rough_night.setChecked(False)