# ==================================================
# Black Feather Foundry
#
# File:
# ui/achievement_page.py
#
# Purpose:
# Achievement Desk.
#
# Prepare Achievement Runs, send them to OBS,
# and archive completed runs.
#
# ==================================================

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.components.foundry_card import FoundryCard

from widgets.run_details import RunDetails
from widgets.achievement_list import AchievementList
from widgets.run_notes import RunNotes
from widgets.run_result import RunResult
from widgets.achievement_actions import AchievementActions

from widgets.achievement_stats import (
    AchievementPointsCard,
    AchievementRatioCard,
    CategoryProgressCard,
    CustomStatCard,
    AchievementDetailsPanel,
)

from services.settings_service import SettingsService
from services.archive_service import ArchiveService
from services.obs_websocket_service import ObsWebSocketService
from services.eso_achievement_database_service import (
    EsoAchievementDatabaseService,
)
from services.achievement_progress_service import (
    AchievementProgressService,
)
from services.achievement_stats_service import (
    AchievementStatsService,
)


class AchievementPage(QWidget):
    """
    Achievement Desk.
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

        #
        # Achievement stats (read-only game database +
        # local progress tracking).
        #

        data_dir = Path(__file__).resolve().parents[1] / "data"

        self.eso_data_service = EsoAchievementDatabaseService(
            data_dir / "eso.db"
        )

        self.achievement_progress_service = AchievementProgressService(
            data_dir / "achievement_progress.json"
        )

        self.achievement_stats_service = AchievementStatsService(
            self.eso_data_service,
            self.achievement_progress_service,
        )

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        # --------------------------------------------------
        # Header
        # --------------------------------------------------

        self.header = FoundryHeader(
            title="Achievement Desk",
            subtitle="Prepare and archive Achievement Runs.",
            department="Operations",
        )

        # --------------------------------------------------
        # Widgets
        # --------------------------------------------------

        self.details = RunDetails()

        self.achievements = AchievementList()

        self.notes = RunNotes()

        self.result = RunResult()

        self.actions = AchievementActions()

        self.status = FoundryStatusBar()

        # --------------------------------------------------
        # Achievement Stats
        # --------------------------------------------------

        self.points_stat = AchievementPointsCard()

        self.earned_stat = AchievementRatioCard()

        self.category_stat = CategoryProgressCard()

        self.dungeons_stat = AchievementRatioCard()

        self.trials_stat = AchievementRatioCard()

        self.custom_stat = CustomStatCard()

        self.achievement_details = AchievementDetailsPanel(
            self.eso_data_service,
            self.achievement_progress_service,
        )

        # --------------------------------------------------
        # Main Layout
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Achievement Stats Row
        # --------------------------------------------------

        stats_widget = QWidget()

        stats_layout = QHBoxLayout(stats_widget)

        stats_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        stats_layout.setSpacing(12)

        points_card = FoundryCard(
            "Achievement Points"
        )

        points_card.addWidget(
            self.points_stat
        )

        stats_layout.addWidget(
            points_card
        )

        earned_card = FoundryCard(
            "Earned"
        )

        earned_card.addWidget(
            self.earned_stat
        )

        stats_layout.addWidget(
            earned_card
        )

        category_card = FoundryCard(
            "Category Progress"
        )

        category_card.addWidget(
            self.category_stat
        )

        stats_layout.addWidget(
            category_card
        )

        dungeons_card = FoundryCard(
            "Dungeons"
        )

        dungeons_card.addWidget(
            self.dungeons_stat
        )

        stats_layout.addWidget(
            dungeons_card
        )

        trials_card = FoundryCard(
            "Trials"
        )

        trials_card.addWidget(
            self.trials_stat
        )

        stats_layout.addWidget(
            trials_card
        )

        custom_card = FoundryCard(
            "Custom"
        )

        custom_card.addWidget(
            self.custom_stat
        )

        stats_layout.addWidget(
            custom_card
        )

        layout.addWidget(
            stats_widget,
            0,
        )

        # --------------------------------------------------
        # Achievement Details
        # --------------------------------------------------

        details_stats_card = FoundryCard(
            "Achievement Details"
        )

        details_stats_card.addWidget(
            self.achievement_details
        )

        details_stats_card.setMinimumHeight(
            160
        )

        layout.addWidget(
            details_stats_card,
            0,
        )

        # --------------------------------------------------
        # Run Details
        # --------------------------------------------------

        details_card = FoundryCard(
            "Run Details"
        )

        details_card.addWidget(
            self.details
        )

        details_card.setMinimumHeight(
            170
        )

        layout.addWidget(
            details_card,
            0,
        )

        # --------------------------------------------------
        # Achievements
        # --------------------------------------------------

        achievements_card = FoundryCard(
            "Achievements"
        )

        achievements_card.addWidget(
            self.achievements
        )

        achievements_card.setMinimumHeight(
            220
        )

        layout.addWidget(
            achievements_card,
            1,
        )

        # --------------------------------------------------
        # Bottom Row
        # --------------------------------------------------

        bottom_widget = QWidget()

        bottom_layout = QHBoxLayout(
            bottom_widget
        )

        bottom_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        bottom_layout.setSpacing(12)

        # --------------------------------------------------
        # Run Notes
        # --------------------------------------------------

        notes_card = FoundryCard(
            "Run Notes"
        )

        notes_card.addWidget(
            self.notes
        )

        notes_card.setMinimumHeight(
            190
        )

        # --------------------------------------------------
        # Run Result
        # --------------------------------------------------

        result_card = FoundryCard(
            "Run Result"
        )

        result_card.addWidget(
            self.result
        )

        result_card.setMinimumHeight(
            190
        )

        bottom_layout.addWidget(
            notes_card,
            3,
        )

        bottom_layout.addWidget(
            result_card,
            2,
        )

        layout.addWidget(
            bottom_widget,
            1,
        )

        # --------------------------------------------------
        # Actions
        # --------------------------------------------------

        layout.addWidget(
            self.actions,
            0,
        )

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        layout.addWidget(
            self.status,
            0,
        )

        self.status.info(
            "Ready to prepare an Achievement Run."
        )

        # --------------------------------------------------
        # Populate Stats
        # --------------------------------------------------

        self.category_stat.set_categories(
            self.achievement_stats_service.top_categories()
        )

        self.refresh_stats()

    # --------------------------------------------------
    # Signals
    # --------------------------------------------------

    def connect_signals(self):

        self.actions.prepareRequested.connect(
            self.prepare_run
        )

        self.actions.sendRequested.connect(
            self.send_to_obs
        )

        self.actions.archiveRequested.connect(
            self.archive_run
        )

        self.actions.clearRequested.connect(
            self.clear_run
        )

        self.category_stat.picker.currentTextChanged.connect(
            self.update_category_stat
        )

    # --------------------------------------------------
    # Achievement Stats
    # --------------------------------------------------

    def refresh_stats(self):
        """
        Recompute every stat box from the current
        progress state.
        """

        self.achievement_stats_service.refresh()

        overall = self.achievement_stats_service.overall()

        self.points_stat.set_points(
            overall["points_earned"]
        )

        self.earned_stat.set_ratio(
            overall["count_earned"],
            overall["count_total"],
        )

        dungeons = self.achievement_stats_service.category(
            "Dungeons"
        )

        self.dungeons_stat.set_ratio(
            dungeons["count_earned"],
            dungeons["count_total"],
        )

        trials = self.achievement_stats_service.category(
            "Trials"
        )

        self.trials_stat.set_ratio(
            trials["count_earned"],
            trials["count_total"],
        )

        self.update_category_stat()

    def update_category_stat(self):
        """
        Refresh the points earned / total for whichever
        category is currently selected.
        """

        category = self.category_stat.current_category()

        if not category:
            return

        progress = self.achievement_stats_service.category(
            category
        )

        self.category_stat.set_ratio(
            progress["points_earned"],
            progress["points_total"],
        )

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def prepare_run(self):

        number = (
            self.archive.peek_number("AR") + 1
        )

        run_id = self.archive.format_id(
            "AR",
            number,
        )

        self.details.run_number.setText(
            run_id
        )

        self.status.success(
            f"Prepared {run_id}"
        )

    def send_to_obs(self):

        #
        # OBS integration comes later.
        #

        self.status.success(
            "Achievement Run sent to OBS."
        )

    def archive_run(self):

        #
        # Archive implementation comes later.
        #

        self.status.success(
            "Achievement Run archived."
        )

    def clear_run(self):

        self.details.clear()

        self.achievements.clear()

        self.notes.clear()

        self.result.clear()

        self.status.info(
            "Achievement Run cleared."
        )