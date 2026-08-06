# ==================================================
# Black Feather Foundry
#
# File:
# ui/incident_page.py
#
# Purpose:
# Incident Desk page.
#
# Prepare Incident Reports, send them to OBS,
# and archive completed reports.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from widgets.page_header import PageHeader
from widgets.status_panel import StatusPanel

from ui.components.section_card import SectionCard

from widgets.incident_editor import IncidentEditor
from widgets.incident_actions import IncidentActions

from services.settings_service import SettingsService
from services.archive_service import ArchiveService
from services.obs_websocket_service import ObsWebSocketService


class IncidentPage(QWidget):
    """
    Incident Desk.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()

        self.build_ui()

        self.connect_signals()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------

    def build_services(self):

        self.settings = SettingsService(
            Path("settings.json")
        ).load()

        self.archive_service = ArchiveService(
            counters_folder=Path(
                self.settings["CountersFolder"]
            ),
            archive_folder=Path(
                self.settings["ArchiveFolder"]
            ),
        )

        self.obs = ObsWebSocketService(
            host=self.settings["ObsWebSocketHost"],
            port=self.settings["ObsWebSocketPort"],
            password=self.settings["ObsWebSocketPassword"],
        )

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = PageHeader(
            title="Incident Desk",
            subtitle="Prepare and file today's incident report.",
            department="Administration",
        )

        self.editor = IncidentEditor()

        self.actions = IncidentActions()

        self.status = StatusPanel()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.header)

        editor = SectionCard("Incident Report")
        editor.addWidget(self.editor)

        layout.addWidget(editor)

        layout.addStretch()

        layout.addWidget(self.actions)

        layout.addWidget(self.status)

        self.status.info(
            "Ready to prepare an incident report."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.actions.generateRequested.connect(
            self.generate_report_number
        )

        self.actions.sendRequested.connect(
            self.save_to_obs
        )

        self.actions.archiveRequested.connect(
            self.archive
        )

        self.actions.clearRequested.connect(
            self.clear
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def generate_report_number(self):

        number = (
            self.archive_service.peek_number("IR") + 1
        )

        report_id = self.archive_service.format_id(
            "IR",
            number,
        )

        self.editor.report_number.setText(
            report_id
        )

        self.status.success(
            f"Prepared {report_id}"
        )

    def save_to_obs(self):

        model = self.editor.model

        self.obs.update_incident_report(model)

        self.status.success(
            "Incident report sent to OBS."
        )

    def archive(self):

        model = self.editor.model

        report_id, path = self.archive_service.file_form(
            "IR",
            lambda report_id, number: [

                f"# Incident Report {report_id}",

                "",

                f"Location: {model.Location}",

                f"Department: {model.Department}",

                f"Severity: {model.Severity}",

                "",

                model.Summary,

            ],
        )

        self.editor.report_number.setText(
            report_id
        )

        self.status.success(
            f"Archived as {report_id}"
        )

    def clear(self):

        self.editor.clear()

        self.status.info(
            "Incident report cleared."
        )