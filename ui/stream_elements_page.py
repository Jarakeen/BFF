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
    QHBoxLayout,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_card import FoundryCard
from ui.foundry_page import FoundryPage
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


class LiveOperationsPage(FoundryPage):
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

        # --------------------------------------------------
        # Settings
        # --------------------------------------------------

        self.settings = SettingsService(
            Path("settings.json")
        ).load()

        root = Path(
            self.settings["BffRoot"]
        )

        # --------------------------------------------------
        # Domain Services
        # --------------------------------------------------

        self.expedition = ExpeditionService()

        self.raid = RaidService(
            self.expedition
        )

        root = Path(
            self.settings["BffRoot"]
        )

        self.narrator = NarratorService(
            root / "Natural_history_narrator.md"
        )

        print("Narrator file:", self.narrator.content_path)
        print("Exists:", self.narrator.content_path.exists())

        # --------------------------------------------------
        # External Services
        # --------------------------------------------------

        self.obs = ObsWebSocketService(
            host=self.settings["ObsWebSocketHost"],
            port=self.settings["ObsWebSocketPort"],
            password=self.settings["ObsWebSocketPassword"],
        )

        # --------------------------------------------------
        # Archive
        # --------------------------------------------------

        self.archive = ArchiveService(
            counters_folder=Path(
                self.settings["CountersFolder"]
            ),
            archive_folder=Path(
                self.settings["ArchiveFolder"]
            ),
        )

    def build_ui(self):

        print("OBS Service:", self.obs)
        #
        # Header
        #

        self.header = FoundryHeader(
            title="Live Operations",
            subtitle="Run the current expedition and record its progress.",
            department="Operations",
            )

        

        self.set_header(self.header)

        #
        # Widgets
        #

        self.session = SessionPanel()

        self.raid_controls = RaidControls()

        self.timeline = TimelinePanel()

        self.narrator_panel = NarratorPanel(
            self.narrator
        )

        self.stream = StreamControls()

        self.status = FoundryStatusBar()

        #
        # Workspace
        #

        workspace_widget = QWidget()

        workspace = QHBoxLayout(workspace_widget)

        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(12)

        #
        # Left Column
        #

        left = QVBoxLayout()

        session = FoundryCard("Expedition Session")
        session.addWidget(self.session)

        raid = FoundryCard("Raid Controls")
        raid.addWidget(self.raid_controls)

        stream = FoundryCard("Stream Controls")
        stream.addWidget(self.stream)

        left.addWidget(session)
        left.addWidget(raid)
        left.addWidget(stream)

        left.addStretch()
        # #
        # # Right Column
        # #

        right = QVBoxLayout()

        narrator = FoundryCard("Narrator")
        narrator.addWidget(self.narrator_panel)

        timeline = FoundryCard("Timeline")
        timeline.addWidget(self.timeline)

        right.addWidget(narrator)
        right.addWidget(timeline)
        right.addStretch()
        #
        # Assemble
        #

        workspace.addLayout(left, 2)
        workspace.addLayout(right, 3)

        self.add_workspace(workspace_widget)

        #
        # Footer
        #

        self.set_status(self.status)

    def connect_signals(self):

        #
        # Raid Controls
        #

        self.raid_controls.pullStarted.connect(
            self.pull_started
        )

        self.raid_controls.ultPullStarted.connect(
            self.ult_pull
        )

        self.raid_controls.wipeRecorded.connect(
            self.record_wipe
        )

        self.raid_controls.bossCleared.connect(
            self.boss_clear
        )

        #
        # Narrator
        #

        self.narrator_panel.narratorRequested.connect(
            self.post_narrator
        )

        #
        # Stream
        #

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
