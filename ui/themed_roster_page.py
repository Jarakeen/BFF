from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from zoneinfo import available_timezones

from PySide6.QtCore import QTime, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.team_schedule import TeamSchedule
from services.accessibility_preferences import AccessibilityPreferences
from services.build_service import BuildService
from services.finch_shared_provenance_service import format_shared_timestamp
from services.finch_shared_import_service import (
    import_shared_team_from_finch,
    list_shared_teams_from_finch,
)
from services.finch_shared_publish_service import publish_team_to_finch
from services.roster_share_formats import discord_roster_text, export_roster_csv
from services.team_schedule_share_export import TeamScheduleShareDocumentExporter
from services.team_deletion_service import delete_team_everywhere
from ui.components.foundry_card import FoundryCard
from ui.roster_page import RosterPage as BaseRosterPage


_DAY_ORDER = (
    ("Mon", "Monday"),
    ("Tue", "Tuesday"),
    ("Wed", "Wednesday"),
    ("Thu", "Thursday"),
    ("Fri", "Friday"),
    ("Sat", "Saturday"),
    ("Sun", "Sunday"),
)

_FINCH_TEAM_PUBLISH_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-team-publish",
)
_FINCH_TEAM_READ_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-team-read",
)

_COMMON_TIMEZONES = (
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Australia/Sydney",
    "Australia/Perth",
    "Asia/Tokyo",
)


class RosterPage(BaseRosterPage):
    """Roster page with team management, schedules, and theme-aware sharing."""

    def _build_ui(self):
        super()._build_ui()
        self._finch_team_publish_future: Future | None = None
        self._finch_team_publish_timer = QTimer(self)
        self._finch_team_publish_timer.setInterval(100)
        self._finch_team_publish_timer.timeout.connect(self._poll_team_publish)
        self._finch_team_read_future: Future | None = None
        self._finch_team_read_mode = ""
        self._finch_team_read_timer = QTimer(self)
        self._finch_team_read_timer.setInterval(100)
        self._finch_team_read_timer.timeout.connect(self._poll_shared_team_read)
        self.tabs.addTab(self._build_team_schedule_tab(), "TEAM SCHEDULE")

        self.export_share_button = QPushButton("Share Roster ▾")
        self.export_share_button.setProperty("primary", True)
        self.export_share_button.setToolTip(
            "Share the visible roster as a themed PDF, Google Sheets-ready CSV, or Discord-formatted text."
        )
        share_menu = QMenu(self.export_share_button)
        pdf_action = share_menu.addAction("Export Themed PDF")
        csv_action = share_menu.addAction("Export for Google Sheets (.csv)")
        share_menu.addSeparator()
        discord_action = share_menu.addAction("Copy Discord Roster")
        pdf_action.triggered.connect(self._export_roster_pdf)
        csv_action.triggered.connect(self._export_roster_csv)
        discord_action.triggered.connect(self._copy_roster_discord)
        self.export_share_button.setMenu(share_menu)
        self.header.add_context_widget(self.export_share_button)

        self.open_player_builds_button = QPushButton("Open Builds")
        self.open_player_builds_button.setToolTip(
            "Open this player's saved characters and builds on the Builds page."
        )
        self.open_player_builds_button.clicked.connect(
            self._open_selected_player_builds
        )
        if hasattr(self, "actions") and self.actions.layout() is not None:
            self.actions.layout().addWidget(self.open_player_builds_button)
        if hasattr(self, "table"):
            self.table.itemDoubleClicked.connect(
                lambda *_: self._open_selected_player_builds()
            )

    def _open_selected_player_builds(self) -> None:
        member_id = (
            self.table.selected_member_id() if hasattr(self, "table") else None
        )
        if member_id is None:
            self.status.warning("Select a personnel record first.")
            return
        member = self.roster_service.get_member(int(member_id))
        if member is None:
            self.status.warning("That personnel record could not be reloaded.")
            return
        gamertag = str(member.PlayerName or "").strip()
        if not gamertag:
            self.status.warning(
                "This personnel record does not have a Gamertag / Player Name yet."
            )
            return
        opener = getattr(self.window(), "_open_player_builds", None)
        if not callable(opener):
            self.status.warning(
                "Build navigation is not available from this window."
            )
            return
        opener(gamertag)

    def _build_team_schedule_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        manage_card = FoundryCard("Teams", "group")
        manage_intro = QLabel(
            "Create and retire named raid teams here. Deleting a team removes its schedule and roster memberships, but never deletes people, characters, or builds."
        )
        manage_intro.setWordWrap(True)
        manage_intro.setProperty("pageSubtitle", True)
        manage_card.addWidget(manage_intro)

        manage_row = QHBoxLayout()
        manage_row.setSpacing(8)
        self.new_team_name = QLineEdit()
        self.new_team_name.setPlaceholderText("New team name...")
        self.new_team_name.returnPressed.connect(self._create_team)
        manage_row.addWidget(self.new_team_name, 1)

        create_team = QPushButton("Create Team")
        create_team.setProperty("primary", True)
        create_team.clicked.connect(self._create_team)
        manage_row.addWidget(create_team)

        delete_team = QPushButton("Delete Selected Team")
        delete_team.setToolTip("Remove the selected team, its schedule, and its roster memberships.")
        delete_team.clicked.connect(self._delete_selected_team)
        manage_row.addWidget(delete_team)
        manage_card.addLayout(manage_row)
        root.addWidget(manage_card)

        card = FoundryCard("Raid Times & Days", "stopwatch")
        intro = QLabel(
            "Keep the recurring raid schedule for each team in the same place. Time zones are stored explicitly so nobody has to perform international clock arithmetic in Discord."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        card.addWidget(intro)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        form.addWidget(QLabel("TEAM"), 0, 0)
        self.schedule_team_combo = QComboBox()
        self.schedule_team_combo.setMinimumWidth(240)
        self.schedule_team_combo.currentTextChanged.connect(self._load_team_schedule)
        form.addWidget(self.schedule_team_combo, 0, 1, 1, 3)

        form.addWidget(QLabel("RAID DAYS"), 1, 0)
        days = QWidget()
        days_layout = QHBoxLayout(days)
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(8)
        self.schedule_day_checks: dict[str, QCheckBox] = {}
        for short, long_name in _DAY_ORDER:
            check = QCheckBox(short)
            check.setToolTip(long_name)
            self.schedule_day_checks[short] = check
            days_layout.addWidget(check)
        days_layout.addStretch(1)
        form.addWidget(days, 1, 1, 1, 3)

        form.addWidget(QLabel("START TIME"), 2, 0)
        self.schedule_time_edit = QTimeEdit()
        self.schedule_time_edit.setDisplayFormat("h:mm AP")
        self.schedule_time_edit.setTime(QTime(20, 0))
        form.addWidget(self.schedule_time_edit, 2, 1)

        form.addWidget(QLabel("TIME ZONE"), 2, 2)
        self.schedule_timezone_combo = QComboBox()
        self.schedule_timezone_combo.setEditable(True)
        zones = list(_COMMON_TIMEZONES)
        seen = set(zones)
        zones.extend(zone for zone in sorted(available_timezones()) if zone not in seen)
        self.schedule_timezone_combo.addItems(zones)
        self.schedule_timezone_combo.setCurrentText("America/New_York")
        self.schedule_timezone_combo.setMinimumWidth(240)
        form.addWidget(self.schedule_timezone_combo, 2, 3)
        card.addLayout(form)

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("SHARE-SHEET PREVIEW"))
        self.schedule_preview = QLabel("Schedule not set")
        self.schedule_preview.setProperty("cardBadge", True)
        preview_row.addWidget(self.schedule_preview, 1)
        save = QPushButton("Save Team Schedule")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_team_schedule)
        preview_row.addWidget(save)

        self.publish_team_finch_button = QPushButton("Publish Team to Finch")
        self.publish_team_finch_button.setToolTip(
            "Publish the selected Team's saved schedule and basic active roster identity to Finch."
        )
        self.publish_team_finch_button.clicked.connect(self._publish_selected_team_to_finch)
        preview_row.addWidget(self.publish_team_finch_button)

        self.get_shared_teams_button = QPushButton("Get Shared Teams")
        self.get_shared_teams_button.setToolTip(
            "Browse Teams published to Finch. Copy to Local creates a new local Team with schedule/focus only; Personnel is never imported."
        )
        self.get_shared_teams_button.clicked.connect(self._get_shared_teams)
        preview_row.addWidget(self.get_shared_teams_button)
        card.addLayout(preview_row)

        for check in self.schedule_day_checks.values():
            check.toggled.connect(self._update_schedule_preview)
        self.schedule_time_edit.timeChanged.connect(self._update_schedule_preview)
        self.schedule_timezone_combo.currentTextChanged.connect(self._update_schedule_preview)

        root.addWidget(card)
        root.addStretch(1)
        return page

    def refresh(self):
        super().refresh()
        if hasattr(self, "schedule_team_combo"):
            self._reload_schedule_teams(self.schedule_team_combo.currentText().strip())

    def _reload_schedule_teams(self, preferred: str = "") -> None:
        names = self.roster_service.list_team_names()
        self.schedule_team_combo.blockSignals(True)
        try:
            self.schedule_team_combo.clear()
            self.schedule_team_combo.addItems(names)
            if preferred:
                index = next(
                    (i for i, name in enumerate(names) if name.casefold() == preferred.casefold()),
                    -1,
                )
                if index >= 0:
                    self.schedule_team_combo.setCurrentIndex(index)
        finally:
            self.schedule_team_combo.blockSignals(False)
        self._load_team_schedule(self.schedule_team_combo.currentText())

    def _create_team(self) -> None:
        name = self.new_team_name.text().strip()
        if not name:
            self.status.warning("Enter a team name first.")
            return
        try:
            canonical = self.roster_service.ensure_team_name(name)
            self.new_team_name.clear()
            self._reload_schedule_teams(canonical)
            self.status.success(f"Team ready: {canonical}. Add raid days and time below when you want them.")
        except Exception as exc:
            self.status.error(f"Team creation failed: {exc}")

    def _delete_selected_team(self) -> None:
        team = self.schedule_team_combo.currentText().strip()
        if not team:
            self.status.warning("Select a team to delete.")
            return

        answer = QMessageBox.question(
            self,
            "Delete Team",
            f'Delete "{team}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            build_service = BuildService(get_data_dir() / "builds.json")
            build_service.load()
            result = delete_team_everywhere(
                self.roster_service,
                build_service,
                team,
            )
            super().refresh()
            self._reload_schedule_teams()
            self.status.success(
                f"Deleted team {result.team_name}: "
                f"{result.removed_memberships} roster membership(s) and "
                f"{result.removed_build_assignments} build assignment(s) removed. "
                "People, characters, builds, and old raid plans were kept."
            )
        except Exception as exc:
            self.status.error(f"Team deletion failed: {exc}")

    def _selected_days_text(self) -> str:
        return ", ".join(
            short for short, _ in _DAY_ORDER
            if self.schedule_day_checks[short].isChecked()
        )

    def _set_selected_days(self, value: str) -> None:
        selected = {piece.strip().casefold() for piece in str(value or "").split(",") if piece.strip()}
        for short, long_name in _DAY_ORDER:
            self.schedule_day_checks[short].setChecked(
                short.casefold() in selected or long_name.casefold() in selected
            )

    def _load_team_schedule(self, team_name: str) -> None:
        if not hasattr(self, "schedule_day_checks"):
            return
        schedule = self.roster_service.get_team_schedule(team_name)
        for check in self.schedule_day_checks.values():
            check.blockSignals(True)
        self.schedule_time_edit.blockSignals(True)
        self.schedule_timezone_combo.blockSignals(True)
        try:
            self._set_selected_days(schedule.RaidDays if schedule else "")
            if schedule and schedule.RaidTime:
                parsed = QTime.fromString(schedule.RaidTime, "h:mm AP")
                if parsed.isValid():
                    self.schedule_time_edit.setTime(parsed)
            timezone = schedule.TimeZone if schedule and schedule.TimeZone else "America/New_York"
            self.schedule_timezone_combo.setCurrentText(timezone)
        finally:
            for check in self.schedule_day_checks.values():
                check.blockSignals(False)
            self.schedule_time_edit.blockSignals(False)
            self.schedule_timezone_combo.blockSignals(False)
        self._update_schedule_preview()

    def _current_team_schedule(self) -> TeamSchedule | None:
        team = self.schedule_team_combo.currentText().strip()
        if not team:
            return None
        return TeamSchedule(
            TeamName=team,
            RaidDays=self._selected_days_text(),
            RaidTime=self.schedule_time_edit.time().toString("h:mm AP"),
            TimeZone=self.schedule_timezone_combo.currentText().strip(),
        )

    def _update_schedule_preview(self, *_args) -> None:
        if not hasattr(self, "schedule_preview"):
            return
        schedule = self._current_team_schedule()
        self.schedule_preview.setText(schedule.display_text if schedule else "Create or select a team first")

    def _save_team_schedule(self) -> None:
        schedule = self._current_team_schedule()
        if schedule is None:
            self.status.warning("Create or select a team before saving raid times.")
            return
        if not schedule.RaidDays:
            self.status.warning("Choose at least one raid day.")
            return
        if not schedule.TimeZone:
            self.status.warning("Choose a time zone so the schedule is unambiguous.")
            return
        try:
            self.roster_service.set_team_schedule(schedule)
            self._update_schedule_preview()
            self.status.success(f"Saved {schedule.TeamName}: {schedule.display_text}")
        except Exception as exc:
            self.status.error(f"Team schedule save failed: {exc}")

    def _publish_selected_team_to_finch(self) -> None:
        team = self.schedule_team_combo.currentText().strip()
        if not team:
            self.status.warning("Select a Team before publishing to Finch.")
            return
        if (
            self._finch_team_publish_future is not None
            and not self._finch_team_publish_future.done()
        ):
            self.status.info("A Finch Team publish is already running.")
            return

        self.publish_team_finch_button.setEnabled(False)
        self.status.info(f"Publishing {team} to Finch…")
        self._finch_team_publish_future = _FINCH_TEAM_PUBLISH_EXECUTOR.submit(
            publish_team_to_finch,
            database_path=Path(get_data_dir()) / "eso.db",
            team_name=team,
            settings_path=Path("settings.json"),
        )
        self._finch_team_publish_timer.start()

    def _poll_team_publish(self) -> None:
        future = self._finch_team_publish_future
        if future is None or not future.done():
            return

        self._finch_team_publish_timer.stop()
        self._finch_team_publish_future = None
        self.publish_team_finch_button.setEnabled(True)
        try:
            result = future.result()
        except Exception as exc:
            self.status.error(f"Finch Team publish failed: {exc}")
            return
        self.status.success(
            f"Published Team to Finch: {result.snapshot_key}"
        )

    def _get_shared_teams(self) -> None:
        if self._finch_team_read_future is not None and not self._finch_team_read_future.done():
            self.status.info("A Finch shared-Team request is already running.")
            return
        self.get_shared_teams_button.setEnabled(False)
        self._finch_team_read_mode = "list"
        self.status.info("Fetching shared Teams from Finch…")
        self._finch_team_read_future = _FINCH_TEAM_READ_EXECUTOR.submit(
            list_shared_teams_from_finch,
            database_path=Path(get_data_dir()) / "eso.db",
            raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
            settings_path=Path("settings.json"),
        )
        self._finch_team_read_timer.start()

    def _poll_shared_team_read(self) -> None:
        future = self._finch_team_read_future
        if future is None or not future.done():
            return

        mode = self._finch_team_read_mode
        self._finch_team_read_future = None
        self._finch_team_read_mode = ""

        try:
            result = future.result()
        except Exception as exc:
            self._finch_team_read_timer.stop()
            self.get_shared_teams_button.setEnabled(True)
            self.status.error(f"Finch shared Team request failed: {exc}")
            return

        if mode == "list":
            previews = tuple(result)
            if not previews:
                self._finch_team_read_timer.stop()
                self.get_shared_teams_button.setEnabled(True)
                self.status.info("Finch has no shared Teams yet.")
                return
            labels = [
                (
                    f"{row.team_name} • {row.member_count} member(s)"
                    + (f" • {row.current_focus}" if row.current_focus else "")
                    + f" • {row.published_by or 'Unknown publisher'}"
                    + f" • {format_shared_timestamp(row.updated_at)}"
                    + f" • {row.provenance}"
                )
                for row in previews
            ]
            selected, ok = QInputDialog.getItem(
                self,
                "Shared Teams on Finch",
                "Copy shared Team to Local:",
                labels,
                0,
                False,
            )
            if not ok:
                self._finch_team_read_timer.stop()
                self.get_shared_teams_button.setEnabled(True)
                self.status.info("Shared Team copy cancelled.")
                return
            index = labels.index(selected)
            preview = previews[index]
            answer = QMessageBox.question(
                self,
                "Copy Shared Team to Local",
                (
                    f'Copy "{preview.team_name}" from Finch into a new local Team?\n\n'
                    f"Published by: {preview.published_by or 'Unknown'}\n"
                    f"Updated: {format_shared_timestamp(preview.updated_at)}\n"
                    f"Status: {preview.provenance}\n\n"
                    "This creates a separate local Team copy with raid schedule, time zone, and current focus. "
                    "It never overwrites an existing Team and does not create Personnel."
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._finch_team_read_timer.stop()
                self.get_shared_teams_button.setEnabled(True)
                self.status.info("Shared Team import cancelled.")
                return
            self._finch_team_read_mode = "import"
            self._finch_team_read_future = _FINCH_TEAM_READ_EXECUTOR.submit(
                import_shared_team_from_finch,
                snapshot_key=preview.snapshot_key,
                database_path=Path(get_data_dir()) / "eso.db",
                raid_plans_path=Path(get_data_dir()) / "raid_plans.json",
                settings_path=Path("settings.json"),
            )
            return

        self._finch_team_read_timer.stop()
        self.get_shared_teams_button.setEnabled(True)
        canonical = str(result or "").strip()
        self._reload_schedule_teams(canonical)
        self.status.success(
            f"Copied shared Team from Finch into local Team: {canonical}."
        )

    def _visible_assignment_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        table = getattr(self, "assignment_table", None)
        if table is None:
            return rows

        for row in range(table.rowCount()):
            def text(column: int) -> str:
                item = table.item(row, column)
                return item.text().strip() if item is not None else ""

            rows.append({
                "player": text(0),
                "role": text(1),
                "class": text(2),
                "build": text(3),
                "primary": text(4),
                "secondary": text(5),
                "gear": text(6),
                "notes": text(7),
                "ready": text(8),
            })
        return rows

    def _share_title(self) -> str:
        if hasattr(self, "view_combo"):
            view = self.view_combo.currentText().strip()
            if view:
                return view
        return "Raid Roster"

    def _export_roster_pdf(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Roster",
            "raid_roster.pdf",
            "Share PDF (*.pdf)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")

        try:
            theme_name = AccessibilityPreferences().visual_theme()
            TeamScheduleShareDocumentExporter().export_roster(
                self.members,
                path,
                assignments=self._visible_assignment_rows(),
                title=self._share_title(),
                theme_name=theme_name,
                team_schedules=self.roster_service.list_team_schedules(),
            )
            self.status.success(f"Exported themed roster to {path}")
        except Exception as exc:
            self.status.error(f"Roster export failed: {exc}")

    def _export_roster_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Roster for Google Sheets",
            "raid_roster.csv",
            "CSV for Google Sheets (*.csv)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".csv":
            path = path.with_suffix(".csv")
        try:
            export_roster_csv(
                path,
                self.members,
                assignments=self._visible_assignment_rows(),
                team_schedules=self.roster_service.list_team_schedules(),
            )
            self.status.success(
                f"Exported Google Sheets-ready roster to {path}. Upload the CSV to Sheets and it will keep the roster columns."
            )
        except Exception as exc:
            self.status.error(f"Roster CSV export failed: {exc}")

    def _copy_roster_discord(self) -> None:
        try:
            text = discord_roster_text(
                self.members,
                assignments=self._visible_assignment_rows(),
                team_schedules=self.roster_service.list_team_schedules(),
                title=self._share_title(),
            )
            QApplication.clipboard().setText(text)
            self.status.success(
                "Copied Discord-formatted roster to the clipboard. Paste it directly into your raid channel."
            )
        except Exception as exc:
            self.status.error(f"Discord roster copy failed: {exc}")
