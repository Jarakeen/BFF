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

import json

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QWidget,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar

from ui.components.foundry_card import FoundryCard


from widgets.broadcast_briefing import BroadcastBriefing
from widgets.broadcast_generator_panel import BroadcastGeneratorPanel
from widgets.broadcast_actions import BroadcastActions
from ui.foundry_page import FoundryPage

from services.settings_service import SettingsService
from services.broadcast_generator import BroadcastGenerator
from services.obs_websocket_service import ObsWebSocketService
from services.archive_service import ArchiveService
from PySide6.QtCore import QTimer

class BroadcastPage(FoundryPage):
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

        self.archive_service = ArchiveService(
            counters_folder=Path(self.settings["CountersFolder"]),
            archive_folder=Path(self.settings["ArchiveFolder"]),
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

        #
        # Header
        #

        self.header = FoundryHeader(
            title="Broadcast Desk",
            subtitle="Prepare today's field dispatch.",
            department="Communications",
        )

        #
        # Widgets
        #

        self.briefing = BroadcastBriefing()

        self.generator_panel = BroadcastGeneratorPanel()

        self.actions = BroadcastActions()

        self.status = FoundryStatusBar()

        #
        # Page
        #

        self.set_header(self.header)

        #
        # Workspace
        #

        workspace_widget = QWidget()

        workspace = QHBoxLayout(workspace_widget)

        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(12)

        #
        # Left Card
        #

        briefing = FoundryCard("Today's Briefing")

        briefing.addWidget(self.briefing)
        briefing.addStretch()

        #
        # Right Card
        #

        preview = FoundryCard("Generated Broadcast")

        preview.addWidget(self.generator_panel)

        #
        # Assemble Workspace
        #

        workspace.addWidget(
            briefing,
            2,
        )

        workspace.addWidget(
            preview,
            3,
        )

        self.add_workspace(workspace_widget)

        #
        # Bottom
        #

        self.set_actions(self.actions)

        self.set_status(self.status)

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

        try:

            model = self.briefing.model

            result = self.generator.generate(model)

            self.generator_panel.set_result(result)

            self.status.success(
                "Broadcast generated."
            )

        except Exception as exc:

            self.status.error(
                f"Generation failed: {exc}"
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

            #
            # OBS's Lua script polls this file the same way
            # it polls StreamEvents.json for Live Operations.
            #

            broadcast_path = Path(
                self.settings["CurrentBroadcastPath"]
            )

            broadcast_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            broadcast_path.write_text(
                json.dumps(
                    {
                        "Title": title,
                        "Notification": notification,
                        "Focus": model.focus,
                        "Location": model.location,
                    },
                    ensure_ascii=False,
                    indent=4,
                ),
                encoding="utf-8",
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

            report_id, path = self.archive_service.file_form(
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

    # --------------------------------------------------
    # Debugg
    # --------------------------------------------------
    
    def inspect_layout(self):

        page = self.stack.currentWidget()

        print("\n==========")
        print(type(page))

        self.dump_widget(page)

    def dump_widget(self, widget, indent=0):

        print(
            " " * indent,
            type(widget).__name__,
            widget.geometry(),
        )

        layout = widget.layout()

        if layout:

            print(
                " " * indent,
                type(layout).__name__,
            )

            for i in range(layout.count()):

                item = layout.itemAt(i)

                if item.widget():

                    self.dump_widget(
                        item.widget(),
                        indent + 4,
                    )    