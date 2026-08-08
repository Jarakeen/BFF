# ==================================================
# Black Feather Foundry
#
# File:
# ui/archive_page.py
#
# Purpose:
# Archive page.
#
# Browse and review archived Expeditions,
# Broadcasts, Field Notes, Incident Reports,
# and other Foundry records.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar

from ui.components.foundry_card import FoundryCard

from widgets.archive_browser import ArchiveBrowser
from widgets.archive_preview import ArchivePreview
from widgets.archive_actions import ArchiveActions

from services.settings_service import SettingsService
from services.archive_service import ArchiveService


class ArchivePage(QWidget):
    """
    Browse archived Foundry records.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()

        self.build_ui()

        self.connect_signals()

        self.refresh()

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

    def build_ui(self):

        # Main page layout
        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(18)

        # Widgets
        self.header = FoundryHeader(
            title="Archive",
            subtitle="Browse previous expeditions and Foundry records.",
            department="Archives",
        )

        self.browser = ArchiveBrowser()
        self.preview = ArchivePreview()
        self.actions = ArchiveActions()
        self.status = FoundryStatusBar()

        # Cards
        browser = FoundryCard("Archive Browser")
        browser.addWidget(self.browser)

        preview = FoundryCard("Preview")
        preview.addWidget(self.preview)

        # Middle row
        content = QHBoxLayout()
        content.addWidget(browser, 1)
        content.addWidget(preview, 2)

        # Assemble page
        layout.addWidget(self.header)
        layout.addLayout(content)
        # layout.addStretch()
        layout.addWidget(self.actions)
        layout.addWidget(self.status)

        self.status.info(
            "Archive ready."
        )

    def connect_signals(self):
            
        self.browser.archiveSelected.connect(
            self.load_archive
        )

        self.actions.refreshRequested.connect(
            self.refresh
        )

        self.actions.openRequested.connect(
            self.open_archive
        )

        self.actions.exportRequested.connect(
            self.export_archive
        )

        self.actions.revealRequested.connect(
            self.reveal_archive
        )

    def refresh(self):
        records = self.archive.list_records()

        self.browser.load_records(records)

        self.status.info(
            f"{len(records)} archive(s) loaded."
        )

    def load_archive(self, archive_no: str):
        """
        Load the selected archive into the preview.
        """

        text = self.archive.load_record(
            archive_no
        )

        self.preview.load_text(text)    

    def open_archive(self):
        pass


    def export_archive(self):
        pass


    def reveal_archive(self):
        pass