# ==================================================
# Black Feather Foundry
#
# File:
# widgets/run_result.py
#
# Purpose:
# Records the outcome of an Achievement Run.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QButtonGroup,
)


class RunResult(QWidget):
    """
    Records the outcome of an Achievement Run.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Result
        #

        self.success = QCheckBox(
            "Success"
        )

        self.partial = QCheckBox(
            "Partial Success"
        )

        self.failed = QCheckBox(
            "Not Today"
        )

        #
        # Only one result may be selected.
        #

        self.result_group = QButtonGroup(self)

        self.result_group.setExclusive(True)

        self.result_group.addButton(self.success)

        self.result_group.addButton(self.partial)

        self.result_group.addButton(self.failed)

        #
        # Final Time
        #

        self.final_time = QLineEdit()

        self.final_time.setPlaceholderText(
            "e.g. 42:18"
        )

        #
        # Layout
        #

        result_row = QHBoxLayout()

        result_row.addWidget(self.success)

        result_row.addWidget(self.partial)

        result_row.addWidget(self.failed)

        result_row.addStretch()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(10)

        layout.addWidget(
            QLabel("Run Result")
        )

        layout.addLayout(
            result_row
        )

        layout.addWidget(
            QLabel("Final Time")
        )

        layout.addWidget(
            self.final_time
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @property
    def result(self) -> str:

        if self.success.isChecked():
            return "Success"

        if self.partial.isChecked():
            return "Partial Success"

        if self.failed.isChecked():
            return "Not Today"

        return ""

    def clear(self):
        """
        Reset the widget.
        """

        self.success.setChecked(False)

        self.partial.setChecked(False)

        self.failed.setChecked(False)

        self.final_time.clear()

    def set_result(
        self,
        result: str,
        final_time: str = "",
    ):
        """
        Populate the widget.
        """

        self.clear()

        if result == "Success":
            self.success.setChecked(True)

        elif result == "Partial Success":
            self.partial.setChecked(True)

        elif result == "Not Today":
            self.failed.setChecked(True)

        self.final_time.setText(
            final_time
        )