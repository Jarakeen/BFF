# ==================================================
# Black Feather Foundry
#
# File:
# ui/stream_elements_page.py
#
# Purpose:
# Stream Elements page.
#
# Operates OBS scenes, overlays, and alerts
# for the live broadcast.
#
# ==================================================

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from widgets.page_header import PageHeader
from widgets.status_panel import StatusPanel
from ui.components.section_card import SectionCard

from widgets.session_panel import SessionPanel
from widgets.raid_controls import RaidControls
from widgets.timeline_panel import TimelinePanel
from widgets.narrator_panel import NarratorPanel
from widgets.stream_controls import StreamControls

from services.settings_service import SettingsService
from services.expedition_service import ExpeditionService
from services.raid_service import RaidService
from services.narrator_service import NarratorService
from services.obs_websocket_service import ObsWebSocketService
from services.archive_service import ArchiveService

class LiveOperationsPage(QWidget):
    """
    Live Operations.

    Run the current expedition and record its progress.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()
        self.build_ui()
        self.connect_signals()

    def build_services(self):

        self.settings = SettingsService(
            Path("settings.json")
        ).load()

        self.expedition = ExpeditionService()

        self.raid = RaidService(
            self.expedition
        )

        self.narrator = NarratorService(
            Path(
                self.settings["NarratorContent"]
            )
        )

        self.obs = ObsWebSocketService(
            host=self.settings["ObsWebSocketHost"],
            port=self.settings["ObsWebSocketPort"],
            password=self.settings["ObsWebSocketPassword"],
        )

        self.archive = ArchiveService(
            counters_folder=Path(
                self.settings["CountersFolder"]
            ),
            archive_folder=Path(
                self.settings["ArchiveFolder"]
            ),
        )

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.header = PageHeader(
            title="Live Operations",
            subtitle="Run the current expedition and record its progress.",
            department="Operations",
        )

        self.session = SessionPanel()

        self.raid_controls = RaidControls()

        self.timeline = TimelinePanel()

        self.narrator_panel = NarratorPanel(
            self.narrator
        )

        self.stream = StreamControls()

        self.status = StatusPanel()

        layout.addWidget(self.header)

        session = SectionCard("Expedition Session")
        session.addWidget(self.session)
        layout.addWidget(session)

        raid = SectionCard("Raid Controls")
        raid.addWidget(self.raid_controls)
        layout.addWidget(raid)

        timeline = SectionCard("Timeline")
        timeline.addWidget(self.timeline)
        layout.addWidget(timeline)

        narrator = SectionCard("Narrator")
        narrator.addWidget(self.narrator_panel)
        layout.addWidget(narrator)

        stream = SectionCard("Stream Controls")
        stream.addWidget(self.stream)
        layout.addWidget(stream)

        layout.addStretch()

        layout.addWidget(self.status)
    def connect_signals(self):

        self.raid_controls.pullRequested.connect(
            self.pull_started
        )

        self.raid_controls.ultPullRequested.connect(
            self.ult_pull
        )

        self.raid_controls.wipeRequested.connect(
            self.record_wipe
        )

        self.raid_controls.bossClearRequested.connect(
            self.boss_clear
        )

        self.narrator_panel.narratorRequested.connect(
            self.post_narrator
        )

        self.stream.brbRequested.connect(
            self.brb
        )

        self.stream.endStreamRequested.connect(
            self.end_stream
        )

        self.stream.resetSessionRequested.connect(
            self.reset_session
        )
    def pull_started(self):
        pass

    def ult_pull(self):
        pass

    def record_wipe(self):
        pass

    def boss_clear(self):
        pass

    def post_narrator(self, category):
        pass

    def brb(self):
        pass

    def end_stream(self):
        pass

    def reset_session(self):
        pass
