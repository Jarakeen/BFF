from __future__ import annotations

"""Add a small portable-calendar action to Roster -> Team Schedule."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox

from services.team_schedule_ics import export_team_schedule_ics
from ui.components.foundry_button import ButtonRole, FoundryButton

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.themed_roster_page import RosterPage

    original = RosterPage._build_team_schedule_tab

    def build_team_schedule_tab_with_calendar(self):
        page = original(self)
        button = FoundryButton("✦ Add to Calendar (.ics)", role=ButtonRole.SECONDARY)
        button.setToolTip(
            "Create a portable recurring calendar event for the selected team. Works with Apple Calendar, Google Calendar, Outlook, and other .ics-compatible calendars."
        )

        def add_to_calendar() -> None:
            schedule = self._current_team_schedule()
            if schedule is None or not schedule.TeamName.strip():
                self.status.warning("Create or select a team before adding it to a calendar.")
                return
            if not schedule.RaidDays.strip() or not schedule.RaidTime.strip() or not schedule.TimeZone.strip():
                self.status.warning("Save raid days, time, and time zone before adding this team to a calendar.")
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
                self.status.success(f"Calendar event ready: {schedule.TeamName}")
            else:
                self.status.success(f"Saved calendar file: {path}")

        button.clicked.connect(add_to_calendar)
        page.layout().insertWidget(max(0, page.layout().count() - 1), button)
        self.add_to_calendar_button = button
        return page

    RosterPage._build_team_schedule_tab = build_team_schedule_tab_with_calendar
    _INSTALLED = True
