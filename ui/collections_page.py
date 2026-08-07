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

from widgets.page_header import PageHeader
from widgets.status_panel import StatusPanel

from ui.components.section_card import SectionCard

from widgets.collection_browser import CollectionBrowser
from widgets.collection_actions import CollectionActions

from services.settings_service import SettingsService
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

        self.settings = SettingsService(
            Path("settings.json")
        ).load()

        try:
            self.progress = AchievementProgressService(
                Path(
                    self.settings["AchievementProgress"]
                )
            )

            self.provider = AchievementProvider(
                data_path=Path(
                    self.settings["AchievementData"]
                ),
                progress=self.progress,
            )

        except KeyError:

            #
            # Temporary development mode
            #

            from services.mock_achievement_provider import (
                MockAchievementProvider,
            )

            self.provider = MockAchievementProvider()

            
    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.header = PageHeader(
            title="Collections",
            subtitle="Browse ESO achievements, collectibles, and discoveries.",
            department="Research",
        )

        self.browser = CollectionBrowser()

        self.actions = CollectionActions()

        self.status = StatusPanel()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(12)

        layout.addWidget(
            self.header
        )

        browser = SectionCard(
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

        self.browser.set_provider(
            self.provider
        )

        self.status.info(
            f"{self.provider.completed_count()} achievements completed."
        )

    def achievement_changed(
        self,
        achievement_id: str,
        complete: bool,
    ):

        self.provider.set_complete(
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