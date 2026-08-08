# ==================================================
# Black Feather Foundry
#
# File:
# ui/collections_page.py
#
# Purpose:
# Collections.
#
# Browse ESO achievements and other
# Tamrielic collections.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar

from ui.components.foundry_card import FoundryCard

from widgets.collection_browser import CollectionBrowser
from widgets.collection_actions import CollectionActions

from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.achievement_progress_service import (
    AchievementProgressService,
)
from services.achievement_provider import (
    AchievementProvider,
)


class CollectionsPage(QWidget):
    """
    Browse Tamrielic collections.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()

        self.build_ui()

        self.connect_signals()

        self.refresh()

    # --------------------------------------------------
    # Services
    # --------------------------------------------------


    def build_services(self):

        data_dir = Path(__file__).resolve().parents[1] / "data"

        self.eso_data_service = EsoAchievementDatabaseService(
            data_dir / "eso.db"
        )

        self.achievement_progress_service = AchievementProgressService(
            data_dir / "achievement_progress.json"
        )
    
            
    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):
        self.header = FoundryHeader(
            title="Collections",
            subtitle="Browse ESO achievements, collectibles, and discoveries.",
            department="Research",
        )

        self.browser = CollectionBrowser(
        provider=self.eso_data_service,
        progress=self.achievement_progress_service,
    )

        self.actions = CollectionActions()

        self.status = FoundryStatusBar()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(8)

        layout.addWidget(
            self.header
        )

        browser = FoundryCard(
            "Achievement Journal"
        )

        browser.addWidget(
            self.browser
        )

        layout.addWidget(
            browser
        )

        # layout.addStretch()

        layout.addWidget(
            self.actions
        )

        layout.addWidget(
            self.status
        )

        self.status.info(
            "Collections ready."
        )

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.browser.achievementChanged.connect(
            self.achievement_changed
        )

        self.actions.refreshRequested.connect(
            self.refresh
        )

        self.actions.syncRequested.connect(
            self.sync
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def refresh(self):

        self.browser.reload()

        self.status.info(
            f"{self.achievement_progress_service.completed_count()} achievements completed."
        )

    def achievement_changed(
        self,
        achievement_id: str,
        complete: bool,
    ):

        self.eso_data_service.set_complete(
            achievement_id,
            complete,
        )

        self.status.success(
            "Progress updated."
        )

    def sync(self):
        """
        Google Sheets sync.

        (Implemented later.)
        """

        self.status.info(
            "Synchronization not implemented yet."
        )