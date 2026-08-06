# ==================================================
# Black Feather Foundry
#
# File:
# ui/broadcast_page.py
#
# Purpose:
# Broadcast Desk page.
#
# Coordinates the briefing, content generation,
# OBS synchronization, and archive operations
# for live broadcasts.
#
# ==================================================

from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from widgets.page_header import PageHeader
from ui.components.section_card import SectionCard
from widgets.status_panel import StatusPanel
from services.archive_service import ArchiveService 
from widgets.broadcast_briefing import BroadcastBriefing
from widgets.broadcast_generator_panel import BroadcastGeneratorPanel
from widgets.broadcast_actions import BroadcastActions
from services.settings_service import  SettingsService
from services.broadcast_generator import BroadcastGenerator
from services.obs_websocket_service import ObsWebSocketService


class BroadcastPage(QWidget):
    """
    Broadcast Desk.

    Generates stream titles, notifications,
    and synchronizes broadcast information
    with OBS.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Services
        #

        self.broadcast_generator = BroadcastGenerator()
        settings = SettingsService(Path("settings.json")).load()

        self.archive_service = ArchiveService(
            counters_folder=Path(SettingsService["CountersFolder"]),
            archive_folder=Path(SettingsService["ArchiveFolder"]),
            session_archive_folder=Path(SettingsService["SessionArchiveFolder"]),
            )


        #
        # Settings
        #

        host=settings["ObsWebSocketHost"],
        port=settings["ObsWebSocketPort"],
        password=settings["ObsWebSocketPassword"],

        #
        # UI
        #

        self.build_ui()

        #
        # Signals
        #

        self.connect_signals()


    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.header = PageHeader(
            title="Broadcast Desk",
            subtitle="Prepare today's field dispatch.",
            department="Communications",
        )

        self.briefing = BroadcastBriefing()

        self.generator_panel = BroadcastGeneratorPanel()

        self.actions = BroadcastActions()

        self.status = StatusPanel()


        layout.addWidget(self.header)

        briefing = SectionCard("Tonight's Briefing")
        briefing.addWidget(self.briefing)
        layout.addWidget(briefing)

        preview = SectionCard("Content Preview")
        preview.addWidget(self.generator_panel)
        layout.addWidget(preview)

        actions = SectionCard("Quick Actions")
        actions.addWidget(self.actions)
        layout.addWidget(actions)

        layout.addStretch()

        layout.addWidget(self.status)

        self.status.info(
            "Ready to prepare today's broadcast."
        )
        

    def connect_signals(self):

        self.actions.generateRequested.connect(
            self.generate
        )

        self.actions.clearRequested.connect(
            self.clear
        )

        self.actions.saveRequested.connect(
            self.save_to_obs
        )

        self.actions.archiveRequested.connect(
            self.archive
        )

    def generate(self):

        model = self.briefing.model

        result = self.generator.generate(model)

        self.generator_panel.set_result(result)

        self.status.success(
            "Generated broadcast package."
        )

    def clear(self):
        """
        Reset the Broadcast Desk.
        """

        self.briefing.clear()

        self.generator_panel.clear()

        self.status.info(
            "Broadcast briefing cleared."
        )


    def save_to_obs(self):
        """
        Update the OBS overlay.
        """

        try:

            model = self.briefing.model

            title = self.generator_panel.selected_title
            notification = self.generator_panel.selected_notification

            if not title or not notification:
                self.status.warning(
                    "Generate a broadcast before sending it to OBS."
                )
                return

            self.obs.update_overlay(
                model=model,
                title=title,
                notification=notification,
            )

            self.status.success(
                "OBS overlay updated."
            )

        except Exception as exc:

            self.status.error(
                f"Failed to update OBS: {exc}"
            )
        

    def archive(self):
        """
        Archive the current broadcast.
        """

        try:

            model = self.briefing.model

            title = self.generator_panel.selected_title

            notification = self.generator_panel.selected_notification

            report_id, path = self.archive_service.file_form(
                "BC",
                lambda report_id, number: [

                    f"# Broadcast {report_id}",

                    "",

                    f"Expedition: {model.focus}",

                    f"Location: {model.location}",

                    f"Difficulty: {', '.join(model.difficulty)}",

                    f"Weather: {model.weather}",

                    f"Coffee Status: {model.coffee}",

                    f"Coffee Level: {model.coffee_level}",

                    f"Engineering: {model.engineering}",

                    f"Incidents: {model.incidents}",

                    f"Team: {model.team}",

                    f"Mood: {model.mood}",

                    "",

                    f"Title: {title}",

                    "",

                    "Notification:",

                    notification,

                ],
            )

            self.status.success(
                f"Archived as {report_id}"
            )

        except Exception as exc:

            self.status.error(
                f"Archive failed: {exc}"
            )

    