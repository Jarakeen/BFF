# ==================================================
# Black Feather Foundry
#
# File:
# widgets/run_details.py
#
# Purpose:
# Run details editor for Achievement Runs.
#
# ==================================================

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
)

from models.achievement_run_model import AchievementRunModel


class RunDetails(QWidget):
    """
    Editor for Achievement Run details.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Run Information
        #

        self.run_number = QLabel("AR-—")

        self.date = QLineEdit(
            datetime.now().strftime("%m / %d / %Y")
        )

        self.content = QComboBox()
        self.content.setEditable(True)

        self.group_size = QSpinBox()
        self.group_size.setRange(1, 24)
        self.group_size.setValue(4)

        #
        # Difficulty
        #

        self.normal = QCheckBox("Normal")
        self.veteran = QCheckBox("Veteran")
        self.hard_mode = QCheckBox("Hard Mode")
        self.perfecta = QCheckBox("Perfecta")

        self.veteran.setChecked(True)

        #
        # Run Type
        #

        self.full_clear = QCheckBox("Full Clear")
        self.achievements_only = QCheckBox(
            "Achievements Only"
        )
        self.speed_run = QCheckBox("Speed Run")
        self.teaching_run = QCheckBox("Teaching Run")

        #
        # Layout
        #

        form = QFormLayout()

        form.addRow(
            "Run Number",
            self.run_number,
        )

        form.addRow(
            "Date",
            self.date,
        )

        form.addRow(
            "Dungeon / Trial",
            self.content,
        )

        form.addRow(
            "Group Size",
            self.group_size,
        )

        difficulty = QHBoxLayout()

        difficulty.addWidget(self.normal)
        difficulty.addWidget(self.veteran)
        difficulty.addWidget(self.hard_mode)
        difficulty.addWidget(self.perfecta)
        difficulty.addStretch()

        form.addRow(
            "Difficulty",
            difficulty,
        )

        run_type = QHBoxLayout()

        run_type.addWidget(self.full_clear)
        run_type.addWidget(self.achievements_only)
        run_type.addWidget(self.speed_run)
        run_type.addWidget(self.teaching_run)
        run_type.addStretch()

        form.addRow(
            "Run Type",
            run_type,
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addLayout(form)

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> AchievementRunModel:

        return AchievementRunModel()

    def set_model(
        self,
        model: AchievementRunModel,
    ):
        """
        Populate the editor from a model.
        """

        pass

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):

        self.set_model(
            AchievementRunModel()
        )