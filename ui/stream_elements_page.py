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

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer, QSize
from PySide6.QtGui import QIcon

from engine.config import get_resource_path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
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

        self.archive_id = None
        self.run_started = False
        self.dirty = False

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

        self.start_run_button = self.status.add_action(
            "",
            self.start_run,
            "Start a new run",
        )

        self.save_button = self.status.add_action(
            "",
            self.save_run,
            "Save current run",
        )

        self.archive_button = self.status.add_action(
            "",
            self.archive_run,
            "Archive current timeline",
        )

        self.edit_timeline_button = self.status.add_action(
            "Edit",
            self.edit_timeline,
            "Edit the selected timeline event",
        )

        self._set_status_icon(
            self.start_run_button,
            "live-operations",
        )

        self._set_status_icon(
            self.save_button,
            "download",
        )

        self._set_status_icon(
            self.archive_button,
            "archive",
        )

        self.status.set_center_text(
            "EXPEDITION SESSION"
        )

        
 
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

        # --------------------------------------------------
        # Restore saved timeline
        # --------------------------------------------------

        saved_events = saved_session.get(
            "Events",
            []
        )

        events = []

        for data in saved_events:
            try:
                events.append(
                    Event.from_dict(data)
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

        self.expedition.expedition.Events = events
        self.timeline.set_events(events)
        
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

        self.timeline.eventChanged.connect(
            self._event_changed
        )

        self.timeline.eventDeleted.connect(
            self._event_deleted
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
        self.dirty = True

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
        self.dirty = True

    def start_run(self):
        """
        Begin a fresh expedition run.

        This does NOT affect OBS stream state.
        """

        confirm = QMessageBox.question(
            self,
            "Start New Run?",
            "This will clear the current Live Operations session,\n"
            "including the timeline and current run information.\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Cancel
            | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.expedition.new()

        self.timeline.clear()
        self.raid_controls.clear()

        self.archive_id = None
        self.run_started = True
        self.dirty = False

        self.status.success(
            "Run started."
        )
        self.status.set_center_text(
            "RUNNING"
        )

    def edit_timeline(self):
        """Open the existing editor for the selected timeline event."""

        if not self.timeline.edit_selected_event():
            self.status.warning(
                "Select a timeline event to edit."
            )


    def archive_run(self):
        """
        Create a new archive or update the existing archive
        for this run.

        Archiving never clears the active expedition.
        """

        events = self.expedition.expedition.Events
        broadcast = self._load_current_broadcast()

        if not events and not broadcast:
            self.status.warning(
                "Nothing to archive yet. Save a Broadcast, Field Note, or timeline event first."
            )
            return

        lines = self._build_archive_lines(broadcast)

        try:

            # ----------------------------------------------
            # Existing archive
            # ----------------------------------------------

            if self.archive_id:

                path = self._write_existing_archive(
                    self.archive_id,
                    lines,
                )

                self.dirty = False

                self.status.success(
                    f"{self.archive_id} updated."
                )
                self.status.set_center_text(
                    f"ARCHIVE {self.archive_id}"
                )

                return

            # ----------------------------------------------
            # First archive
            # ----------------------------------------------

            archive_id, path = self.archive.file_form(
                "EX",
                lambda report_id, number: lines,
            )

            self.archive_id = archive_id
            self.dirty = False

            self.status.success(
                f"{archive_id} archived."
            )

        except Exception as exc:

            self.status.error(
                f"Archive failed: {exc}"
            )    

    def _build_archive_lines(
        self,
        broadcast: dict | None = None,
    ) -> list[str]:
        """
        Build one end-of-session archive from Live Operations,
        Broadcast, and Field Notes data.
        """

        boss = self._current_boss()

        events = sorted(
            self.expedition.expedition.Events,
            key=lambda event: event.timestamp,
        )

        lines = [
            "# Expedition Archive",
            "",
            f"**Boss:** {boss}",
            "",
        ]

        self._add_broadcast_archive_lines(
            lines,
            broadcast or {},
        )

        lines.extend([
            "## Timeline",
            "",
        ])

        for event in events:

            timestamp = event.timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            detail = event.event

            if event.payload.get("percent") is not None:
                detail += (
                    f" • {event.payload['percent']}%"
                )

            if event.payload.get("pull") is not None:
                detail += (
                    f" • Pull {event.payload['pull']}"
                )

            lines.append(
                f"- `{timestamp}` — {detail}"
            )

            if event.notes:
                lines.append(
                    f"  - Note: {event.notes}"
                )

        return lines

    def _load_current_broadcast(self) -> dict:
        """Read the OBS snapshot without changing its established format."""

        path = Path(self.settings["CurrentBroadcastPath"])

        if not path.exists():
            return {}

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        return data if isinstance(data, dict) else {}

    def _add_broadcast_archive_lines(
        self,
        lines: list[str],
        broadcast: dict,
    ) -> None:
        """Append the saved Broadcast and Field Notes snapshot to an archive."""

        broadcast_fields = (
            ("Title", "Title"),
            ("Notification", "Notification"),
            ("Team", "Team"),
            ("Expedition", "Expedition"),
            ("Location", "Location"),
            ("Objective", "Objective"),
            ("Focus", "Focus"),
            ("Difficulty", "Difficulty"),
            ("Mood", "Mood"),
            ("Weather", "Weather"),
            ("Coffee", "Coffee"),
            ("CoffeeLevel", "Coffee Level"),
            ("Engineering", "Engineering"),
            ("Incidents", "Incidents"),
        )

        saved_broadcast = [
            (label, str(broadcast[key]).strip())
            for key, label in broadcast_fields
            if str(broadcast.get(key, "")).strip()
        ]

        if saved_broadcast:
            lines.extend(["## Broadcast", ""])
            lines.extend(
                f"- **{label}:** {value}"
                for label, value in saved_broadcast
            )
            lines.append("")

        field_notes_present = any(
            key in broadcast
            for key in (
                "Assignment",
                "Observation",
                "Context",
                "NextSteps",
                "RandomNotes",
                "Status",
            )
        )

        if not field_notes_present:
            return

        lines.extend(["## Field Notes", ""])

        assignment = str(broadcast.get("Assignment", "")).strip()
        if assignment:
            lines.extend([f"**Assignment:** {assignment}", ""])

        status = broadcast.get("Status", {})
        if isinstance(status, dict):
            selected_statuses = [
                label
                for key, label in (
                    ("Observe", "Observe"),
                    ("Document", "Document"),
                    ("Learn", "Learn"),
                    ("ShareTheLesson", "Share the Lesson"),
                )
                if status.get(key)
            ]
            if selected_statuses:
                lines.extend([
                    f"**Status:** {', '.join(selected_statuses)}",
                    "",
                ])

        for key, heading in (
            ("Observation", "Observation"),
            ("Context", "Context"),
            ("NextSteps", "Next Steps"),
            ("RandomNotes", "Random Notes"),
        ):
            value = str(broadcast.get(key, "")).strip()
            if value:
                lines.extend([f"### {heading}", "", value, ""])



    def save_run(self):
        """
        Persist the current expedition state.
        """

        events = [
            event.to_dict()
            for event in self.expedition.expedition.Events
        ]

        boss = self._current_boss()

        pulls = len(
            self._boss_events(
                boss,
                "Pull Started",
            )
        )

        wipes = len(
            self._boss_events(
                boss,
                "Wipe",
            )
        )

        self.stream_events.save_session(
            {
                "TotalPulls": pulls,
                "CurrentBoss": boss,
                "BossPulls": pulls,
                "BossWipes": wipes,
                "Events": events,
            }
        )

        self.dirty = False

        self.status.success(
            "Run saved."
        )
        self.status.set_center_text(
            "SAVED"
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
        self.dirty = True

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
        self.dirty = True
        
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
        self.dirty = True

        # --------------------------------------------------
        # Edit
        # --------------------------------------------------


    def _event_changed(self, event):

        self.status.success(
            f"Updated {event.event} at "
            f"{event.timestamp.strftime('%H:%M:%S')}"
        )

        self._refresh_session()
        self.dirty = True



    def _event_deleted(self, event):

        if event in self.expedition.expedition.Events:
            self.expedition.expedition.Events.remove(
                event
            )

        self.status.warning(
            f"Removed {event.event}"
        )

        self._refresh_session()
        self.dirty = True

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
        self.dirty = True

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
        self.dirty = True
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
            "Events": [],
        })

        self.archive_id = None
        self.run_started = False
        self.dirty = False

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

    def _set_status_icon(self, button, icon_name: str):
        """Use one of the real Foundry SVG icons for a status action."""
        icon_path = get_resource_path("assets", "icons", f"{icon_name}.svg")

        if not icon_path.exists():
            return

        button.setText("")
        button.setIcon(
            QIcon(str(icon_path))
        )
        button.setIconSize(
            QSize(18, 18)
        )

    def _write_existing_archive(
        self,
        archive_id: str,
        lines: list[str],
    ) -> Path:
        """Update an existing archive without allocating a new ID."""
        filename = archive_id.replace("-", "_") + ".md"
        path = self.archive.archive_folder / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Archive does not exist: {archive_id}"
            )

        path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return path

    def _mark_dirty(self):
        self.dirty = True
        self.status.warning(
            "Unsaved changes."
        )

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
