# ==================================================
# Black Feather Foundry
#
# File:
# ui/achievement_page.py
#
# Purpose:
# Achievement Desk.
#
# Prepare Achievement Runs, send them to OBS,
# and archive completed runs.
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

from widgets.run_details import RunDetails
from widgets.achievement_list import AchievementList
from widgets.run_notes import RunNotes
from widgets.run_result import RunResult
from widgets.achievement_actions import AchievementActions

from services.settings_service import SettingsService
from services.archive_service import ArchiveService
from services.obs_websocket_service import ObsWebSocketService


class AchievementPage(QWidget):
    """
    Achievement Desk.
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

        self.archive = ArchiveService(
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
            title="Achievement Desk",
            subtitle="Prepare and archive Achievement Runs.",
            department="Operations",
        )

        self.details = RunDetails()

        self.achievements = AchievementList()

        self.notes = RunNotes()

        self.result = RunResult()

        self.actions = AchievementActions()

        self.status = StatusPanel()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(12)

        #
        # Header
        #

        layout.addWidget(
            self.header
        )

        #
        # Run Details
        #

        details = SectionCard(
            "Run Details"
        )

        details.addWidget(
            self.details
        )

        layout.addWidget(
            details
        )

        #
        # Achievement List
        #

        achievements = SectionCard(
            "Achievements"
        )

        achievements.addWidget(
            self.achievements
        )

        layout.addWidget(
            achievements
        )

        #
        # Notes
        #

        notes = SectionCard(
            "Run Notes"
        )

        notes.addWidget(
            self.notes
        )

        layout.addWidget(
            notes
        )

        #
        # Result
        #

        result = SectionCard(
            "Run Result"
        )

        result.addWidget(
            self.result
        )

        layout.addWidget(
            result
        )

        layout.addStretch()

        layout.addWidget(
            self.actions
        )

        layout.addWidget(
            self.status
        )

        self.status.info(
            "Ready to prepare an Achievement Run."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.actions.prepareRequested.connect(
            self.prepare_run
        )

        self.actions.sendRequested.connect(
            self.send_to_obs
        )

        self.actions.archiveRequested.connect(
            self.archive_run
        )

        self.actions.clearRequested.connect(
            self.clear_run
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def prepare_run(self):

        number = (
            self.archive.peek_number("AR") + 1
        )

        run_id = self.archive.format_id(
            "AR",
            number,
        )

        self.details.run_number.setText(
            run_id
        )

        self.status.success(
            f"Prepared {run_id}"
        )

    def send_to_obs(self):

        #
        # OBS integration comes later.
        #

        self.status.success(
            "Achievement Run sent to OBS."
        )

    def archive_run(self):

        #
        # Archive implementation comes later.
        #

        self.status.success(
            "Achievement Run archived."
        )

    def clear_run(self):

        self.details.clear()

        self.achievements.clear()

        self.notes.clear()

        self.result.clear()

        self.status.info(
            "Achievement Run cleared."
        )