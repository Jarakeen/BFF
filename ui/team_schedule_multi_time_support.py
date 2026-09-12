from __future__ import annotations

"""Allow one team to keep different recurring times on different raid days."""

from zoneinfo import available_timezones

from PySide6.QtCore import QTime, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
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
    QCheckBox,
    QComboBox,
)

from models.team_schedule import TeamSchedule, TeamScheduleSlot
from services.team_schedule_ics import export_team_schedule_ics
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard

_INSTALLED = False

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


def _time_edit(hour: int, minute: int = 0) -> QTimeEdit:
    edit = QTimeEdit()
    edit.setDisplayFormat("h:mm AP")
    edit.setTime(QTime(hour, minute))
    return edit


def _set_time(edit: QTimeEdit, value: str, fallback: QTime) -> None:
    parsed = QTime.fromString(str(value or "").strip(), "h:mm AP")
    edit.setTime(parsed if parsed.isValid() else fallback)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    def build_team_schedule_tab(self) -> QWidget:
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

        card = FoundryCard("Raid Times, Days & Focus", "stopwatch")
        intro = QLabel(
            "Keep the recurring schedule and the team's current progression target together. The Teams overview uses this focus exactly as entered; it never guesses what a team is working on."
        )
        intro.setWordWrap(True)
        intro.setProperty("pageSubtitle", True)
        card.addWidget(intro)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)

        form.addWidget(QLabel("TEAM"), 0, 0)
        self.schedule_team_combo = QComboBox()
        self.schedule_team_combo.setMinimumWidth(240)
        self.schedule_team_combo.currentTextChanged.connect(self._load_team_schedule)
        form.addWidget(self.schedule_team_combo, 0, 1, 1, 3)

        form.addWidget(QLabel("CURRENT FOCUS"), 1, 0)
        self.schedule_focus_edit = QLineEdit()
        self.schedule_focus_edit.setPlaceholderText("e.g. Godslayer cleanup, Gryphon Heart, Xalvakka HM...")
        form.addWidget(self.schedule_focus_edit, 1, 1, 1, 3)

        form.addWidget(QLabel("DAY"), 2, 0)
        form.addWidget(QLabel("START"), 2, 1)
        form.addWidget(QLabel("END"), 2, 2)

        self.schedule_day_checks = {}
        self.schedule_start_edits = {}
        self.schedule_end_edits = {}

        for index, (short, long_name) in enumerate(_DAY_ORDER, start=3):
            check = QCheckBox(short)
            check.setToolTip(long_name)
            start = _time_edit(20, 0)
            end = _time_edit(22, 0)
            start.setEnabled(False)
            end.setEnabled(False)

            self.schedule_day_checks[short] = check
            self.schedule_start_edits[short] = start
            self.schedule_end_edits[short] = end

            check.toggled.connect(start.setEnabled)
            check.toggled.connect(end.setEnabled)
            check.toggled.connect(self._update_schedule_preview)
            start.timeChanged.connect(self._update_schedule_preview)
            end.timeChanged.connect(self._update_schedule_preview)

            form.addWidget(check, index, 0)
            form.addWidget(start, index, 1)
            form.addWidget(end, index, 2)

        form.addWidget(QLabel("TIME ZONE"), 10, 0)
        self.schedule_timezone_combo = QComboBox()
        self.schedule_timezone_combo.setEditable(True)
        zones = list(_COMMON_TIMEZONES)
        seen = set(zones)
        zones.extend(zone for zone in sorted(available_timezones()) if zone not in seen)
        self.schedule_timezone_combo.addItems(zones)
        self.schedule_timezone_combo.setCurrentText("America/New_York")
        self.schedule_timezone_combo.setMinimumWidth(240)
        self.schedule_timezone_combo.currentTextChanged.connect(self._update_schedule_preview)
        form.addWidget(self.schedule_timezone_combo, 10, 1, 1, 2)
        card.addLayout(form)

        self.schedule_time_edit = self.schedule_start_edits["Mon"]

        preview_row = QHBoxLayout()
        preview_row.addWidget(QLabel("SHARE-SHEET PREVIEW"))
        self.schedule_preview = QLabel("Schedule not set")
        self.schedule_preview.setProperty("cardBadge", True)
        self.schedule_preview.setWordWrap(True)
        preview_row.addWidget(self.schedule_preview, 1)

        save = QPushButton("Save Team Schedule")
        save.setProperty("primary", True)
        save.clicked.connect(self._save_team_schedule)
        preview_row.addWidget(save)
        card.addLayout(preview_row)
        root.addWidget(card)

        calendar_button = FoundryButton("✦ Add to Calendar (.ics)", role=ButtonRole.SECONDARY)
        calendar_button.setToolTip(
            "Export each selected raid day at its own recurring time. Works with Apple Calendar, Google Calendar, Outlook, and other .ics-compatible calendars."
        )

        def add_to_calendar() -> None:
            schedule = self._current_team_schedule()
            if schedule is None or not schedule.TeamName.strip():
                self.status.warning("Create or select a team before adding it to a calendar.")
                return
            if not schedule.effective_slots or not schedule.TimeZone.strip():
                self.status.warning("Choose at least one raid day, its times, and a time zone first.")
                return
            safe_name = "_".join(schedule.TeamName.strip().split()) or "raid_schedule"
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Add Team Schedule to Calendar",
                f"{safe_name}.ics",
                "Calendar Event (*.ics)",
            )
            if not filename:
                return
            try:
                path = export_team_schedule_ics(schedule, filename)
            except Exception as exc:
                QMessageBox.critical(self, "Calendar export failed", str(exc))
                return
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
            if opened:
                self.status.success(f"Calendar events ready: {schedule.TeamName}")
            else:
                self.status.success(f"Saved calendar file: {path}")

        calendar_button.clicked.connect(add_to_calendar)
        self.add_to_calendar_button = calendar_button
        root.addWidget(calendar_button)
        root.addStretch(1)
        return page

    def current_schedule(self) -> TeamSchedule | None:
        team = self.schedule_team_combo.currentText().strip()
        if not team:
            return None
        slots = []
        for short, _long_name in _DAY_ORDER:
            if not self.schedule_day_checks[short].isChecked():
                continue
            start = self.schedule_start_edits[short].time().toString("h:mm AP")
            end = self.schedule_end_edits[short].time().toString("h:mm AP")
            slots.append(TeamScheduleSlot(Day=short, StartTime=start, EndTime=end))
        return TeamSchedule(
            TeamName=team,
            RaidDays=", ".join(slot.Day for slot in slots),
            RaidTime=slots[0].StartTime if slots else "",
            TimeZone=self.schedule_timezone_combo.currentText().strip(),
            Slots=tuple(slots),
            CurrentFocus=self.schedule_focus_edit.text().strip(),
        )

    def update_preview(self, *_args) -> None:
        if not hasattr(self, "schedule_preview"):
            return
        schedule = current_schedule(self)
        self.schedule_preview.setText(
            schedule.display_text if schedule else "Create or select a team first"
        )

    def load_schedule(self, team_name: str) -> None:
        if not hasattr(self, "schedule_day_checks"):
            return
        schedule = self.roster_service.get_team_schedule(team_name)
        slots_by_day = {
            slot.Day.strip().casefold(): slot
            for slot in (schedule.effective_slots if schedule else ())
        }
        for short, long_name in _DAY_ORDER:
            check = self.schedule_day_checks[short]
            start = self.schedule_start_edits[short]
            end = self.schedule_end_edits[short]
            check.blockSignals(True)
            start.blockSignals(True)
            end.blockSignals(True)
            try:
                slot = slots_by_day.get(short.casefold()) or slots_by_day.get(long_name.casefold())
                checked = slot is not None
                check.setChecked(checked)
                start.setEnabled(checked)
                end.setEnabled(checked)
                if slot is not None:
                    _set_time(start, slot.StartTime, QTime(20, 0))
                    if slot.EndTime:
                        _set_time(end, slot.EndTime, QTime(22, 0))
                    else:
                        end.setTime(start.time().addSecs(3 * 60 * 60))
                else:
                    start.setTime(QTime(20, 0))
                    end.setTime(QTime(22, 0))
            finally:
                check.blockSignals(False)
                start.blockSignals(False)
                end.blockSignals(False)

        self.schedule_timezone_combo.blockSignals(True)
        self.schedule_focus_edit.blockSignals(True)
        try:
            timezone = schedule.TimeZone if schedule and schedule.TimeZone else "America/New_York"
            self.schedule_timezone_combo.setCurrentText(timezone)
            self.schedule_focus_edit.setText(schedule.CurrentFocus if schedule else "")
        finally:
            self.schedule_timezone_combo.blockSignals(False)
            self.schedule_focus_edit.blockSignals(False)
        update_preview(self)

    def save_schedule(self) -> None:
        schedule = current_schedule(self)
        if schedule is None:
            self.status.warning("Create or select a team before saving raid times.")
            return
        if not schedule.effective_slots:
            self.status.warning("Choose at least one raid day.")
            return
        if not schedule.TimeZone:
            self.status.warning("Choose a time zone so the schedule is unambiguous.")
            return
        for slot in schedule.effective_slots:
            start = QTime.fromString(slot.StartTime, "h:mm AP")
            end = QTime.fromString(slot.EndTime, "h:mm AP")
            if not start.isValid() or not end.isValid() or start == end:
                self.status.warning(f"Give {slot.Day} a valid start and end time.")
                return
        try:
            self.roster_service.set_team_schedule(schedule)
            update_preview(self)
            if hasattr(self, "_refresh_team_cards"):
                self._refresh_team_cards()
            focus = f" · Focus: {schedule.CurrentFocus}" if schedule.CurrentFocus else ""
            self.status.success(f"Saved {schedule.TeamName}: {schedule.display_text}{focus}")
        except Exception as exc:
            self.status.error(f"Team schedule save failed: {exc}")

    RosterPage._build_team_schedule_tab = build_team_schedule_tab
    RosterPage._current_team_schedule = current_schedule
    RosterPage._update_schedule_preview = update_preview
    RosterPage._load_team_schedule = load_schedule
    RosterPage._save_team_schedule = save_schedule
    _INSTALLED = True
