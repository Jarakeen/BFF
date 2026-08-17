# ==================================================
# Black Feather Foundry
#
# File:
# ui/collections_page.py
#
# Purpose:
# Achievements.
#
# Browse, track, and review ESO achievements.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QSizePolicy,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_card import FoundryCard

from widgets.collection_browser import CollectionBrowser
from widgets.collection_actions import CollectionActions
from widgets.achievement_stats import (
    AchievementPointsCard,
    AchievementRatioCard,
    AchievementDetailsPanel,
)

from services.eso_achievement_database_service import (
    EsoAchievementDatabaseService,
)

from services.achievement_progress_service import (
    AchievementProgressService,
)

from services.achievement_stats_service import (
    AchievementStatsService,
)


class CollectionsPage(QWidget):
    """
    Achievements workspace.

    Layout:

        Header

        Achievement Points | Earned | Dungeons | Trials | PvP

        Categories | Achievements | Achievement Details

        Existing Actions / Status footer
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.build_services()
        self.build_ui()
        self.connect_signals()
        self.refresh()

    # ==================================================
    # Services
    # ==================================================

    def build_services(self):

        data_dir = (
            Path(__file__).resolve().parents[1]
            / "data"
        )

        # --------------------------------------------------
        # ESO achievement database
        # --------------------------------------------------

        self.eso_data_service = (
            EsoAchievementDatabaseService(
                data_dir / "eso.db"
            )
        )

        # --------------------------------------------------
        # Local completion tracking
        # --------------------------------------------------

        self.achievement_progress_service = (
            AchievementProgressService(
                data_dir / "achievement_progress.json"
            )
        )

        # --------------------------------------------------
        # Statistics
        # --------------------------------------------------

        self.achievement_stats_service = (
            AchievementStatsService(
                self.eso_data_service,
                self.achievement_progress_service,
            )
        )

    # ==================================================
    # UI
    # ==================================================

    def build_ui(self):

        # --------------------------------------------------
        # Header
        # --------------------------------------------------

        self.header = FoundryHeader(
            title="Achievements",
            subtitle="Browse and track ESO achievements.",
            department="Research",
        )

        # --------------------------------------------------
        # Statistics
        # --------------------------------------------------

        self.points_stat = (
            AchievementPointsCard()
        )

        self.earned_stat = (
            AchievementRatioCard()
        )

        self.dungeons_stat = (
            AchievementRatioCard()
        )

        self.trials_stat = (
            AchievementRatioCard()
        )

        self.pvp_stat = (
            AchievementRatioCard()
        )

       

        # --------------------------------------------------
        # Achievement browser
        #
        # IMPORTANT:
        # This is NOT wrapped in FoundryCard.
        #
        # We use a persistent host widget so the
        # CollectionBrowser has a stable Qt parent.
        # --------------------------------------------------

        self.browser_host = QWidget()

        self.browser_host.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        browser_layout = QVBoxLayout(
            self.browser_host
        )

        browser_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        browser_layout.setSpacing(0)

        self.browser = CollectionBrowser(
            provider=self.eso_data_service,
            progress=self.achievement_progress_service,
            parent=self.browser_host,
        )

        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        browser_layout.addWidget(
            self.browser
        )

        # --------------------------------------------------
        # Achievement details
        # --------------------------------------------------

        self.achievement_details = (
            AchievementDetailsPanel(
                self.eso_data_service,
                self.achievement_progress_service,
            )
        )

        # --------------------------------------------------
        # Actions / Status
        # --------------------------------------------------

        self.actions = CollectionActions()

        self.status = FoundryStatusBar()

        # ==================================================
        # Main Page Layout
        # ==================================================

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )

        layout.setSpacing(12)

        # --------------------------------------------------
        # Header
        # --------------------------------------------------

        layout.addWidget(
            self.header,
            0,
        )

        # ==================================================
        # Statistics Row
        # ==================================================

        stats_widget = QWidget()

        stats_layout = QHBoxLayout(
            stats_widget
        )

        stats_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        stats_layout.setSpacing(12)

        # --------------------------------------------------
        # Achievement Points
        # --------------------------------------------------

        points_card = FoundryCard(
            "Achievement Points"
        )

        points_card.addWidget(
            self.points_stat
        )

        stats_layout.addWidget(
            points_card,
            1,
        )

        # --------------------------------------------------
        # Earned
        # --------------------------------------------------

        earned_card = FoundryCard(
            "Earned"
        )

        earned_card.addWidget(
            self.earned_stat
        )

        stats_layout.addWidget(
            earned_card,
            1,
        )

        # --------------------------------------------------
        # Dungeons
        # --------------------------------------------------

        dungeons_card = FoundryCard(
            "Dungeons"
        )

        dungeons_card.addWidget(
            self.dungeons_stat
        )

        stats_layout.addWidget(
            dungeons_card,
            1,
        )

        # --------------------------------------------------
        # Trials
        # --------------------------------------------------

        trials_card = FoundryCard(
            "Trials"
        )

        trials_card.addWidget(
            self.trials_stat
        )

        stats_layout.addWidget(
            trials_card,
            1,
        )

        # --------------------------------------------------
        # PvP
        # --------------------------------------------------

        pvp_card = FoundryCard(
            "PvP"
        )

        pvp_card.addWidget(
            self.pvp_stat
        )

        stats_layout.addWidget(
            pvp_card,
            1,
        )

        layout.addWidget(
            stats_widget,
            0,
        )

        # ==================================================
        # Three Column Workspace
        # ==================================================

        workspace = QWidget()

        workspace_layout = QHBoxLayout(
            workspace
        )

        workspace_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        workspace_layout.setSpacing(12)

       
        # --------------------------------------------------
        # Achievements
        #
        # No "Achievement Journal" card.
        # The browser has its own internal UI.
        # --------------------------------------------------

        workspace_layout.addWidget(
            self.browser_host,
            3,
        )

        # --------------------------------------------------
        # Achievement Details
        # --------------------------------------------------

        details_card = FoundryCard(
            "Achievement Details"
        )

        details_card.setProperty(
            "achievementDetailsCard",
            True,
        )

        details_card.addWidget(
            self.achievement_details
        )

        workspace_layout.addWidget(
            details_card,
            2,
        )

        # --------------------------------------------------
        # Workspace
        # --------------------------------------------------

        layout.addWidget(
            workspace,
            1,
        )

        # ==================================================
        # Footer
        # ==================================================

        layout.addWidget(
            self.actions,
            0,
        )

        layout.addWidget(
            self.status,
            0,
        )

        self.status.info(
            "Achievements ready."
        )

        # --------------------------------------------------
        # Initial statistics
        # --------------------------------------------------

        self.refresh_stats()

    # ==================================================
    # Signals
    # ==================================================

    def connect_signals(self):

        # --------------------------------------------------
        # Achievement completion
        # --------------------------------------------------

        self.browser.achievementChanged.connect(
            self.achievement_changed
        )

        # --------------------------------------------------
        # Achievement selection
        # --------------------------------------------------

        self.browser.achievementSelected.connect(
            self.achievement_details.load_achievement
        )

        # --------------------------------------------------
        # Actions
        # --------------------------------------------------

        self.actions.refreshRequested.connect(
            self.refresh
        )

        self.actions.syncRequested.connect(
            self.sync
        )

    # ==================================================
    # Achievement Progress
    # ==================================================

    def achievement_changed(
        self,
        achievement_id: int,
        complete: bool,
    ):
        """
        Store completion state and immediately update
        the statistics.

        Achievement IDs are integers, matching the
        CollectionBrowser signal.
        """

        self.achievement_progress_service.set_complete(
            achievement_id,
            complete,
        )

        self.refresh_stats()

        self.status.success(
            "Progress updated."
        )

    # ==================================================
    # Statistics
    # ==================================================

    def refresh_stats(self):
        """
        Recalculate the five dashboard statistics.

        IMPORTANT:
        This method does NOT call itself.
        """

        self.achievement_stats_service.refresh()

        overall = (
            self.achievement_stats_service
            .overall()
        )

        # --------------------------------------------------
        # Overall
        # --------------------------------------------------

        self.points_stat.set_points(
            overall["points_earned"]
        )

        self.earned_stat.set_ratio(
            overall["count_earned"],
            overall["count_total"],
        )

        # --------------------------------------------------
        # Dungeons
        # --------------------------------------------------

        dungeons = (
            self.achievement_stats_service
            .category("Dungeons")
        )

        self.dungeons_stat.set_ratio(
            dungeons["count_earned"],
            dungeons["count_total"],
        )

        # --------------------------------------------------
        # Trials
        # --------------------------------------------------

        trials = (
            self.achievement_stats_service
            .category("Trials")
        )

        self.trials_stat.set_ratio(
            trials["count_earned"],
            trials["count_total"],
        )

        # --------------------------------------------------
        # PvP
        # --------------------------------------------------

        pvp = (
            self.achievement_stats_service
            .category("Player vs. Player")
        )

        self.pvp_stat.set_ratio(
            pvp["count_earned"],
            pvp["count_total"],
        )

    # ==================================================
    # Refresh
    # ==================================================

    def refresh(self):

        self.browser.reload()

        self.refresh_stats()

        self.status.info(
            f"{self.achievement_progress_service.completed_count()} "
            "achievements completed."
        )

    # ==================================================
    # Sync
    # ==================================================

    def sync(self):
        """
        Google Sheets synchronization placeholder.
        """

        self.status.info(
            "Synchronization not implemented yet."
        )