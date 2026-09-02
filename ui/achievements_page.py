"""ESO account achievements workspace.

Canonical replacement for the historically misnamed ``collections_page.py``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.achievement_progress_service import AchievementProgressService
from services.achievement_stats_service import AchievementStatsService
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.google_sheet_progress_importer import GoogleSheetProgressImporter
from services.google_sheets_service import (
    COLUMN_FOR_PERSON,
    GoogleSheetsNotConfigured,
    GoogleSheetsService,
)
from services.profiled_collectible_service import ProfiledCollectibleService
from services.settings_service import SettingsService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from widgets.achievement_stats import AchievementDetailsPanel, AchievementPointsCard, AchievementRatioCard
from widgets.collection_actions import CollectionActions
from widgets.collection_browser import CollectionBrowser


class AchievementsPage(QWidget):
    """Browse and track ESO account achievements by profile."""

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
        self.collectible_progress_service = ProfiledCollectibleService(data_dir / "eso.db")

        settings = SettingsService(Path("settings.json")).load()
        self.google_sheets_service = GoogleSheetsService(
            Path(settings["GoogleCredentialsPath"]),
            str(settings["GoogleSpreadsheetId"]),
        )
        self.google_sheet_importer = GoogleSheetProgressImporter(
            self.eso_data_service,
            self.achievement_progress_service,
            self.collectible_progress_service,
        )

    @staticmethod
    def _context_field(title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setProperty("sidebarHeading", True)
        layout.addWidget(label)
        layout.addWidget(widget)
        return box

    def _build_ui(self):
        self.header = FoundryHeader(
            title="Achievements",
            subtitle="Browse and track ESO account achievements.",
            department="Research",
        )

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(150)
        self.profile_combo.setToolTip("Choose whose achievement progress is displayed.")
        self._reload_profile_combo()
        self.header.add_context_widget(self._context_field("PROFILE", self.profile_combo))

        self.add_profile_button = QPushButton("+ Profile")
        self.add_profile_button.setToolTip("Add another person/account progress profile.")
        self.header.add_context_widget(self.add_profile_button)

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
        self.profile_combo.currentTextChanged.connect(self._profile_changed)
        self.add_profile_button.clicked.connect(self._add_profile)
        self.browser.achievementChanged.connect(self.achievement_changed)
        self.browser.achievementSelected.connect(self.achievement_details.load_achievement)
        self.actions.refreshRequested.connect(self.refresh)
        self.actions.syncRequested.connect(self.sync)

    def _reload_profile_combo(self, selected: str | None = None) -> None:
        active = selected or self.achievement_progress_service.active_profile
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.achievement_progress_service.profiles())
        index = self.profile_combo.findText(active)
        self.profile_combo.setCurrentIndex(index if index >= 0 else 0)
        self.profile_combo.blockSignals(False)

    def _profile_changed(self, profile: str) -> None:
        profile = profile.strip()
        if not profile:
            return
        self.achievement_progress_service.set_active_profile(profile)
        self.refresh()

    def _add_profile(self) -> None:
        name, accepted = QInputDialog.getText(self, "Add Achievement Profile", "Profile name")
        if not accepted or not name.strip():
            return
        try:
            profile = self.achievement_progress_service.ensure_profile(name)
            self.achievement_progress_service.set_active_profile(profile)
        except ValueError as exc:
            self.status.warning(str(exc))
            return
        self._reload_profile_combo(profile)
        self.refresh()
        self.status.success(f"Achievement profile ready: {profile}.")

    def achievement_changed(self, achievement_id: int, complete: bool):
        self.achievement_progress_service.set_complete(achievement_id, complete)
        self.refresh_stats()
        self.status.success(
            f"Progress updated for {self.achievement_progress_service.active_profile}."
        )

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
        # Progress can be written by the Settings -> Data Management importer,
        # which owns a separate service instance. Invalidate this page's cache
        # before repainting so imported achievements appear immediately.
        self.achievement_progress_service.reload(preserve_active_profile=True)
        self._reload_profile_combo()
        self.browser.reload()
        self.refresh_stats()
        profile = self.achievement_progress_service.active_profile
        self.status.info(
            f"{self.achievement_progress_service.completed_count()} achievements completed for {profile}."
        )

    @staticmethod
    def _sheet_person_for_profile(profile: str) -> str | None:
        profile_key = str(profile or "").strip().casefold()
        for person in COLUMN_FOR_PERSON:
            if person.casefold() == profile_key:
                return person
        return None

    def _confirm_sheet_import(self, source_person: str, profile: str) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Are you really, really, really sure?")
        dialog.setText("Are you really, really, really sure?")
        dialog.setInformativeText(
            f"This will import checked achievements from {source_person}'s Google Sheet column "
            f"into the local profile '{profile}'. Achievement rewards may also mark canonical "
            "collectibles as owned. Existing local progress is preserved; this import only adds "
            "matched checked items."
        )
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
        yes_button = dialog.button(QMessageBox.StandardButton.Yes)
        if yes_button is not None:
            yes_button.setText("Yes, I am really really really sure")
        return dialog.exec() == QMessageBox.StandardButton.Yes

    def sync(self):
        """Import checked R/J Google Sheet rows into the active named profile."""
        profile = self.achievement_progress_service.active_profile
        source_person = self._sheet_person_for_profile(profile)
        if source_person is None:
            self.status.warning(
                "Google Sheet import requires the active profile to be named Jarakeen or Rylo. "
                "No profile was guessed."
            )
            return

        if not self._confirm_sheet_import(source_person, profile):
            self.status.info("Google Sheet import cancelled. Nothing changed.")
            return

        self.status.info(f"Reading {source_person}'s achievement checkmarks from Google Sheets…")
        try:
            snapshot = self.google_sheets_service.read_achievement_statuses(source_person)
            report = self.google_sheet_importer.import_checked(snapshot, profile=profile)
        except GoogleSheetsNotConfigured as exc:
            self.status.warning(f"Google Sheets is not configured: {exc}")
            return
        except ImportError:
            self.status.warning(
                "Google Sheets support needs the gspread and google-auth packages installed."
            )
            return
        except Exception as exc:
            self.status.error(f"Google Sheet import failed: {exc}")
            return

        self.refresh()
        issue_count = (
            len(report.unresolved_names)
            + len(report.ambiguous_names)
            + len(report.missing_tabs)
        )
        summary = (
            f"Imported {report.matched_achievements} checked achievements for {profile}; "
            f"{report.achievements_added} newly added; "
            f"{report.collectible_rewards_marked} achievement-reward collectibles marked owned."
        )
        if issue_count:
            self.status.warning(
                summary
                + f" Review needed: {len(report.unresolved_names)} unmatched names, "
                f"{len(report.ambiguous_names)} ambiguous names, "
                f"{len(report.missing_tabs)} missing sheet tabs."
            )
        else:
            self.status.success(summary)


# Transitional class alias for callers that imported the old class name.
CollectionsPage = AchievementsPage
