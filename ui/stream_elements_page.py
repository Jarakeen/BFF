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

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
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

from models.event_model import Event

from services.settings_service import SettingsService
from services.expedition_service import ExpeditionService
from services.raid_service import RaidService
from services.narrator_service import NarratorService
from services.obs_websocket_service import ObsWebSocketService
from services.archive_service import ArchiveService
from services.stream_event_service import StreamEventService


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
            root / "nat_his_nar.md"
        )

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

        # --------------------------------------------------
        # Stream Events
        # --------------------------------------------------
        #
        # Writes the trigger file the OBS Lua script polls
        # (chapter markers, log lines, narrator overlay text)
        # and persists session counters so an app restart
        # mid-stream doesn't lose them.
        #

        self.stream_events = StreamEventService(
            events_path=Path(
                self.settings["StreamEventsPath"]
            ),
            session_path=Path(
                self.settings["StreamSessionPath"]
            ),
            boss_log_path=Path(
                self.settings["BossLogPath"]
            ),
        )

    def build_ui(self):

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

        #
        # Restore Session
        #
        # StreamEventService persists counters to disk so an
        # app restart mid-stream doesn't lose them. Best Pull
        # isn't restored here since it's derived from this
        # run's raid events, which start empty on launch.
        #

        saved_session = self.stream_events.load_session()

        self.session.current_boss.setText(
            saved_session["CurrentBoss"]
        )

        self.session.set_total_pulls(
            saved_session["TotalPulls"]
        )

        self.session.set_boss_pulls(
            saved_session["BossPulls"]
        )

        self.session.set_boss_wipes(
            saved_session["BossWipes"]
        )

        #
        # Elapsed Time
        #

        self.elapsed_timer = QTimer(self)

        self.elapsed_timer.setInterval(1000)

        self.elapsed_timer.timeout.connect(
            self._tick_elapsed
        )

        self.elapsed_timer.start()

    def connect_signals(self):

        #
        # Session
        #

        self.session.current_boss.editingFinished.connect(
            self._refresh_session
        )

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

        #
        # OBS (async - the websocket call returns immediately,
        # these signals report what actually happened)
        #

        self.obs.scene_changed.connect(
            self._on_scene_changed
        )

        self.obs.failed.connect(
            self._on_obs_failed
        )

    # --------------------------------------------------
    # Raid Controls
    # --------------------------------------------------

    def pull_started(self):

        boss = self._current_boss()

        pull_number = len(
            self._boss_events(boss, "Pull Started")
        ) + 1

        self.raid.pull_started(
            boss,
            pull_number,
            self.raid_controls.is_first_pull,
        )

        self._log_timeline("Pull Started")

        self._refresh_session()

        self.stream_events.fire_event(
            log_label=f"Pull {pull_number} Started",
        )

        self.status.info(
            f"Pull {pull_number} started on {boss}."
        )

    def ult_pull(self):

        boss = self._current_boss()

        self.raid.ult_pull(boss)

        self._log_timeline("Ult Pull")

        self.stream_events.fire_event(
            log_label="Ult Pull",
        )

        self.status.info(
            f"Ult pull started on {boss}."
        )

    def record_wipe(self, percent: int, rough_night: bool):

        boss = self._current_boss()

        pull_number = len(
            self._boss_events(boss, "Pull Started")
        )

        self.raid.wipe(
            boss,
            pull_number,
            percent,
            rough_night,
        )

        self._log_timeline(f"Reached {percent}%")

        self._refresh_session()

        #
        # A wipe normally earns a narrator note. "Rough
        # night" is the streamer's way of skipping that
        # when it's not the moment for commentary.
        #

        narrator_text = (
            "" if rough_night
            else self.narrator.pick("General")
        )

        self.stream_events.fire_event(
            log_label=f"Wipe - Reached {percent}%",
            narrator_text=narrator_text,
        )

        self.status.warning(
            f"Wipe recorded at {percent}%."
        )

    def boss_clear(self):

        boss = self._current_boss()

        pull_number = len(
            self._boss_events(boss, "Pull Started")
        )

        self.raid.boss_clear(boss, pull_number)

        self._log_timeline("Boss Clear")

        self.stream_events.fire_event(
            chapter_label=f"{boss} Clear",
        )

        boss_pulls = len(
            self._boss_events(boss, "Pull Started")
        )

        boss_wipes = len(
            self._boss_events(boss, "Wipe")
        )

        self.stream_events.append_boss_log(
            boss,
            boss_pulls,
            boss_wipes,
        )

        self.raid_controls.clear()

        self._refresh_session()

        self.status.success(
            f"{boss} cleared!"
        )

    # --------------------------------------------------
    # Narrator
    # --------------------------------------------------

    def post_narrator(self, category):

        text = self.narrator.pick(category)

        if not text:

            self.status.warning(
                f"No narrator lines available for {category}."
            )

            return

        self.stream_events.fire_event(
            narrator_text=text,
            log_label=f"Narrator: {category}",
        )

        self._log_timeline(f"Narrator ({category})")

        self.status.success(
            f"Posted a {category} note."
        )

    # --------------------------------------------------
    # Stream
    # --------------------------------------------------

    def brb(self):

        self.obs.switch_scene(
            self.settings["BrbSceneName"]
        )

        self.stream_events.fire_event(
            log_label="BRB",
        )

        self._log_timeline("BRB")

    def end_stream(self):

        self.obs.switch_scene(
            self.settings["EndOfStreamSceneName"]
        )

        boss = self._current_boss()

        boss_pulls = len(
            self._boss_events(boss, "Pull Started")
        )

        boss_wipes = len(
            self._boss_events(boss, "Wipe")
        )

        if boss_pulls or boss_wipes:

            self.stream_events.append_boss_log(
                boss,
                boss_pulls,
                boss_wipes,
            )

        self.stream_events.fire_event(
            log_label="End Stream",
        )

        self._log_timeline("End Stream")

        self.status.info(
            "Ending stream..."
        )

    def reset_session(self):

        self.expedition.reset()

        self.session.clear()

        self.timeline.clear()

        self.raid_controls.clear()

        self.stream_events.save_session({
            "TotalPulls": 0,
            "CurrentBoss": "",
            "BossPulls": 0,
            "BossWipes": 0,
        })

        self.status.info(
            "Session reset."
        )

    # --------------------------------------------------
    # OBS Callbacks
    # --------------------------------------------------

    def _on_scene_changed(self, scene_name: str):

        self.status.success(
            f"OBS switched to '{scene_name}'."
        )

    def _on_obs_failed(self, message: str):

        self.status.error(
            message
        )

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _current_boss(self) -> str:

        return (
            self.session.current_boss.text().strip()
            or "Unnamed Boss"
        )

    def _boss_events(self, boss: str, event_name: str) -> list:

        return [
            event
            for event in self.expedition.expedition.Events
            if event.category == "Raid"
            and event.event == event_name
            and event.payload.get("boss") == boss
        ]

    def _log_timeline(self, text: str):

        self.timeline.add_event(
            Event(
                category="Raid",
                event=text,
                source="Live Operations",
            )
        )

    def _refresh_session(self):

        boss = self._current_boss()

        boss_pulls = len(
            self._boss_events(boss, "Pull Started")
        )

        boss_wipes = len(
            self._boss_events(boss, "Wipe")
        )

        percentages = [
            event.payload["percent"]
            for event in self._boss_events(boss, "Wipe")
            if "percent" in event.payload
        ]

        best_pull = min(percentages) if percentages else None

        self.session.set_total_pulls(
            self.raid.total_pulls
        )

        self.session.set_boss_pulls(boss_pulls)

        self.session.set_boss_wipes(boss_wipes)

        self.session.set_best_pull(best_pull)

        self.stream_events.save_session({
            "TotalPulls": self.raid.total_pulls,
            "CurrentBoss": boss,
            "BossPulls": boss_pulls,
            "BossWipes": boss_wipes,
        })

    def _tick_elapsed(self):

        start_time = getattr(
            self.expedition.expedition,
            "StartTime",
            None,
        )

        if not start_time:
            return

        elapsed = int(
            (datetime.now() - start_time).total_seconds()
        )

        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.session.set_elapsed_time(
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )
