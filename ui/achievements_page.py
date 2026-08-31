"""ESO account achievements workspace.

Canonical replacement for the historically misnamed ``collections_page.py``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from engine.config import get_data_dir
from services.achievement_progress_service import AchievementProgressService
from services.achievement_stats_service import AchievementStatsService
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from widgets.achievement_stats import AchievementDetailsPanel, AchievementPointsCard, AchievementRatioCard
from widgets.collection_actions import CollectionActions
from widgets.collection_browser import CollectionBrowser


class AchievementsPage(QWidget):
    """Browse and track ESO account achievements."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_services()
        self._build_ui()
        self._connect_signals()
        self.refresh()

    def _build_services(self):
        data_dir = get_data_dir()
        self.eso_data_service = EsoAchievementDatabaseService(data_dir / "eso.db")
        self.achievement_progress_service = AchievementProgressService(data_dir / "achievement_progress.json")
        self.achievement_stats_service = AchievementStatsService(
            self.eso_data_service,
            self.achievement_progress_service,
        )

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Achievements",
            subtitle="Browse and track ESO account achievements.",
            department="Research",
        )

        self.points_stat = AchievementPointsCard()
        self.earned_stat = AchievementRatioCard()
        self.dungeons_stat = AchievementRatioCard()
        self.trials_stat = AchievementRatioCard()
        self.pvp_stat = AchievementRatioCard()

        self.browser_host = QWidget()
        self.browser_host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        browser_layout = QVBoxLayout(self.browser_host)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(0)
        self.browser = CollectionBrowser(
            provider=self.eso_data_service,
            progress=self.achievement_progress_service,
            parent=self.browser_host,
        )
        self.browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        browser_layout.addWidget(self.browser)

        self.achievement_details = AchievementDetailsPanel(
            self.eso_data_service,
            self.achievement_progress_service,
        )
        self.actions = CollectionActions()
        self.status = FoundryStatusBar()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self.header)

        stats = QHBoxLayout()
        for title, widget in (
            ("Achievement Points", self.points_stat),
            ("Earned", self.earned_stat),
            ("Dungeons", self.dungeons_stat),
            ("Trials", self.trials_stat),
            ("PvP", self.pvp_stat),
        ):
            card = FoundryCard(title)
            card.addWidget(widget)
            stats.addWidget(card, 1)
        layout.addLayout(stats)

        workspace = QHBoxLayout()
        workspace.setSpacing(12)
        workspace.addWidget(self.browser_host, 3)
        details_card = FoundryCard("Achievement Details")
        details_card.setProperty("achievementDetailsCard", True)
        details_card.addWidget(self.achievement_details)
        workspace.addWidget(details_card, 2)
        layout.addLayout(workspace, 1)
        layout.addWidget(self.actions)
        layout.addWidget(self.status)
        self.status.info("Achievements ready.")

    def _connect_signals(self):
        self.browser.achievementChanged.connect(self.achievement_changed)
        self.browser.achievementSelected.connect(self.achievement_details.load_achievement)
        self.actions.refreshRequested.connect(self.refresh)
        self.actions.syncRequested.connect(self.sync)

    def achievement_changed(self, achievement_id: int, complete: bool):
        self.achievement_progress_service.set_complete(achievement_id, complete)
        self.refresh_stats()
        self.status.success("Progress updated.")

    def refresh_stats(self):
        self.achievement_stats_service.refresh()
        overall = self.achievement_stats_service.overall()
        self.points_stat.value.setText(f"{overall['points_earned']:,} / {overall['points_total']:,}")
        self.earned_stat.set_ratio(overall["count_earned"], overall["count_total"])

        dungeons = self.achievement_stats_service.category("Dungeons")
        self.dungeons_stat.set_ratio(dungeons["count_earned"], dungeons["count_total"])
        trials = self.achievement_stats_service.category("Trials")
        self.trials_stat.set_ratio(trials["count_earned"], trials["count_total"])
        pvp = self.achievement_stats_service.category("Player vs. Player")
        self.pvp_stat.set_ratio(pvp["count_earned"], pvp["count_total"])

    def refresh(self):
        self.browser.reload()
        self.refresh_stats()
        self.status.info(f"{self.achievement_progress_service.completed_count()} achievements completed.")

    def sync(self):
        self.status.info("Synchronization not implemented yet.")


# Transitional class alias for callers that imported the old class name.
CollectionsPage = AchievementsPage
