from __future__ import annotations

from pathlib import Path
from zoneinfo import available_timezones

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from models.team_schedule import TeamSchedule
from services.accessibility_preferences import AccessibilityPreferences
from services.team_schedule_share_export import TeamScheduleShareDocumentExporter
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
        self.tabs.addTab(self._build_team_schedule_tab(), "TEAM SCHEDULE")

        self.export_share_button = QPushButton("Export / Share")
        self.export_share_button.setProperty("primary", True)
        self.export_share_button.setToolTip(
            "Export the visible raid assignments, team raid times, and personnel roster as a themed PDF."
        )
        self.export_share_button.clicked.connect(self._export_roster_pdf)
        self.header.add_context_widget(self.export_share_button)

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
            deleted = self.roster_service.delete_team(team)
            if not deleted:
                self.status.warning(f"Team no longer exists: {team}")
                return
            super().refresh()
            self._reload_schedule_teams()
            self.status.success(
                f"Deleted team {team}. Roster people, characters, and builds were kept."
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

        title = "Raid Roster"
        if hasattr(self, "view_combo"):
            view = self.view_combo.currentText().strip()
            if view:
                title = view

        try:
            theme_name = AccessibilityPreferences().visual_theme()
            TeamScheduleShareDocumentExporter().export_roster(
                self.members,
                path,
                assignments=self._visible_assignment_rows(),
                title=title,
                theme_name=theme_name,
                team_schedules=self.roster_service.list_team_schedules(),
            )
            self.status.success(f"Exported themed roster to {path}")
        except Exception as exc:
            self.status.error(f"Roster export failed: {exc}")
