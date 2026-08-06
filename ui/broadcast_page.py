# ==================================================
# Black Feather Foundry
#
# File:
# ui/broadcast_page.py
#
# Purpose:
# Broadcast Desk page.
#
# Prepare broadcast information, generate
# titles and notifications, synchronize
# with OBS, and archive broadcasts.
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

from widgets.broadcast_briefing import BroadcastBriefing
from widgets.broadcast_generator_panel import BroadcastGeneratorPanel
from widgets.broadcast_actions import BroadcastActions

from services.settings_service import SettingsService
from services.broadcast_generator import BroadcastGenerator
from services.obs_websocket_service import ObsWebSocketService
from services.archive_service import ArchiveService


class BroadcastPage(QWidget):
    """
    Broadcast Desk.

    Prepare stream information for OBS.
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

        self.generator = BroadcastGenerator()

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
            title="Broadcast Desk",
            subtitle="Prepare today's field dispatch.",
            department="Communications",
        )

        self.briefing = BroadcastBriefing()

        self.generator_panel = BroadcastGeneratorPanel()

        self.actions = BroadcastActions()

        self.status = StatusPanel()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.header)

        briefing = SectionCard("Today's Briefing")
        briefing.addWidget(self.briefing)
        layout.addWidget(briefing)

        preview = SectionCard("Generated Content")
        preview.addWidget(self.generator_panel)
        layout.addWidget(preview)

        actions = SectionCard("Actions")
        actions.addWidget(self.actions)
        layout.addWidget(actions)

        layout.addStretch()

        layout.addWidget(self.status)

        self.status.info(
            "Broadcast Desk ready."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.actions.generateRequested.connect(
            self.generate
        )

        self.actions.saveRequested.connect(
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

    def generate(self):

        model = self.briefing.model

        result = self.generator.generate(
            model
        )

        self.generator_panel.set_result(
            result
        )

        self.status.success(
            "Broadcast generated."
        )

    def save_to_obs(self):

        try:

            model = self.briefing.model

            title = self.generator_panel.selected_title

            notification = (
                self.generator_panel.selected_notification
            )

            if not title or not notification:

                self.status.warning(
                    "Generate a broadcast first."
                )

                return

            self.obs.update_overlay(
                model=model,
                title=title,
                notification=notification,
            )

            self.status.success(
                "Broadcast sent to OBS."
            )

        except Exception as exc:

            self.status.error(
                str(exc)
            )

    def archive(self):

        try:

            model = self.briefing.model

            title = self.generator_panel.selected_title

            notification = (
                self.generator_panel.selected_notification
            )

            report_id, path = self.archive.file_form(
                "FN",
                lambda report_id, number: [

                    f"# Broadcast {report_id}",

                    "",

                    f"Focus: {model.focus}",

                    f"Location: {model.location}",

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

    def clear(self):

        self.briefing.clear()

        self.generator_panel.clear()

        self.status.info(
            "Broadcast cleared."
        )