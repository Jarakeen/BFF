# ==================================================
# Black Feather Foundry
#
# File:
# widgets/incident_editor.py
#
# Purpose:
# Editor for Incident Reports.
#
# ==================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
)

from models.incident_model import (
    IncidentModel,
    ResponsiblePartyFlags,
    IncidentStatusFlags,
)


class IncidentEditor(QWidget):
    """
    Editor for Incident Reports.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Report
        #

        self.report_number = QLabel("Unfiled")

        self.location = QLineEdit()

        self.department = QLineEdit()

        self.severity = QComboBox()

        self.severity.addItems(
            [
                "Minor",
                "Moderate",
                "Major",
                "Critical",
            ]
        )

        #
        # Details
        #

        self.summary = QTextEdit()

        self.suspected_cause = QLineEdit()

        self.observations = QTextEdit()

        self.engineering = QTextEdit()

        self.coffee = QLineEdit()

        #
        # Responsible Party
        #

        self.moose_gremlin = QCheckBox(
            "Moose Gremlin"
        )

        self.lag = QCheckBox(
            "Lag"
        )

        self.user_error = QCheckBox(
            "User Error"
        )

        self.eso = QCheckBox(
            "ESO"
        )

        self.unknown = QCheckBox(
            "Unknown"
        )

        self.under_investigation = QCheckBox(
            "Under Investigation"
        )

        #
        # Status
        #

        self.filed = QCheckBox(
            "Filed"
        )

        self.pending_review = QCheckBox(
            "Pending Review"
        )

        self.follow_up = QCheckBox(
            "Requires Follow-Up"
        )

        self.archived = QCheckBox(
            "Archived"
        )

        #
        # Layout
        #

        report_form = QFormLayout()

        report_form.addRow(
            "Report Number",
            self.report_number,
        )

        report_form.addRow(
            "Location",
            self.location,
        )

        report_form.addRow(
            "Department",
            self.department,
        )

        report_form.addRow(
            "Severity",
            self.severity,
        )

        report_form.addRow(
            "Summary",
            self.summary,
        )

        report_form.addRow(
            "Suspected Cause",
            self.suspected_cause,
        )

        report_form.addRow(
            "Observations",
            self.observations,
        )

        report_form.addRow(
            "Engineering Assessment",
            self.engineering,
        )

        report_form.addRow(
            "Coffee Recommendation",
            self.coffee,
        )

        party_box = QGroupBox(
            "Responsible Party"
        )

        party_layout = QVBoxLayout(
            party_box
        )

        party_layout.addWidget(
            self.moose_gremlin
        )

        party_layout.addWidget(
            self.lag
        )

        party_layout.addWidget(
            self.user_error
        )

        party_layout.addWidget(
            self.eso
        )

        party_layout.addWidget(
            self.unknown
        )

        party_layout.addWidget(
            self.under_investigation
        )

        status_box = QGroupBox(
            "Status"
        )

        status_layout = QVBoxLayout(
            status_box
        )

        status_layout.addWidget(
            self.filed
        )

        status_layout.addWidget(
            self.pending_review
        )

        status_layout.addWidget(
            self.follow_up
        )

        status_layout.addWidget(
            self.archived
        )

        side = QVBoxLayout()

        side.addWidget(
            party_box
        )

        side.addWidget(
            status_box
        )

        side.addStretch()

        body = QHBoxLayout()

        body.addLayout(
            report_form,
            2,
        )

        body.addLayout(
            side,
            1,
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.addLayout(
            body
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> IncidentModel:

        return IncidentModel()

    def set_model(
        self,
        model: IncidentModel,
    ):
        """
        Populate the editor from an IncidentModel.
        """

        pass

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def clear(self):
        """
        Reset the editor.
        """

        self.set_model(
            IncidentModel()
        )