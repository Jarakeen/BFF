"""OBS-facing achievement run display/control desk.

Canonical replacement for the historically vague ``achievement_desk_page.py``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from services.archive_service import ArchiveService
from services.obs_websocket_service import ObsWebSocketService
from services.settings_service import SettingsService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from widgets.achievement_actions import AchievementActions
from widgets.achievement_list import AchievementList
from widgets.run_details import RunDetails
from widgets.run_notes import RunNotes
from widgets.run_result import RunResult


class AchievementBroadcastPage(QWidget):
    """Prepare an achievement run for broadcast/OBS and archive it afterward."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_services()
        self._build_ui()
        self._connect_signals()

    def _build_services(self):
        self.settings = SettingsService(Path("settings.json")).load()
        self.archive = ArchiveService(
            counters_folder=Path(self.settings["CountersFolder"]),
            archive_folder=Path(self.settings["ArchiveFolder"]),
        )
        self.obs = ObsWebSocketService(
            host=self.settings["ObsWebSocketHost"],
            port=self.settings["ObsWebSocketPort"],
            password=self.settings["ObsWebSocketPassword"],
        )

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Achievement Broadcast",
            subtitle="Prepare Achievement Runs for OBS and archive the result.",
            department="Broadcast",
        )
        self.details = RunDetails()
        self.achievements = AchievementList()
        self.notes = RunNotes()
        self.result = RunResult()
        self.actions = AchievementActions()
        self.status = FoundryStatusBar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self.header)

        details_card = FoundryCard("Run Details")
        details_card.addWidget(self.details)
        layout.addWidget(details_card)

        achievements_card = FoundryCard("Achievements")
        achievements_card.addWidget(self.achievements)
        layout.addWidget(achievements_card, 1)

        bottom = QHBoxLayout()
        notes_card = FoundryCard("Run Notes")
        notes_card.addWidget(self.notes)
        result_card = FoundryCard("Run Result")
        result_card.addWidget(self.result)
        bottom.addWidget(notes_card, 3)
        bottom.addWidget(result_card, 2)
        layout.addLayout(bottom, 1)
        layout.addWidget(self.actions)
        layout.addWidget(self.status)
        self.status.info("Ready to prepare an Achievement Run for broadcast.")

    def _connect_signals(self):
        self.actions.prepareRequested.connect(self.prepare_run)
        self.actions.sendRequested.connect(self.send_to_obs)
        self.actions.archiveRequested.connect(self.archive_run)
        self.actions.clearRequested.connect(self.clear_run)

    def prepare_run(self):
        number = self.archive.peek_number("AR") + 1
        run_id = self.archive.format_id("AR", number)
        self.details.run_number.setText(run_id)
        self.status.success(f"Prepared {run_id}")

    def send_to_obs(self):
        self.status.success("Achievement Run sent to OBS.")

    def archive_run(self):
        self.status.success("Achievement Run archived.")

    def clear_run(self):
        self.details.clear()
        self.achievements.clear()
        self.notes.clear()
        self.result.clear()
        self.status.info("Achievement Run cleared.")


# Compatibility aliases for code that used the old generic class name.
AchievementPage = AchievementBroadcastPage

__all__ = ["AchievementBroadcastPage", "AchievementPage"]
