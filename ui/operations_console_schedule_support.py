from __future__ import annotations

"""Use the roster's saved team schedules on the Raid Engine overview.

The overview originally shipped with decorative example raids. This layer
replaces them with the durable schedules already saved on Roster -> Team
Schedule, so the overview remains a summary of real user data rather than a
second pretend calendar.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.roster_service import RosterService
from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_LEGACY_PLACEHOLDER_TEAM_NAMES = {"godslayer composition"}


def _saved_schedules():
    service = RosterService(EsoDatabase(get_data_dir() / "eso.db"))
    schedules = service.list_team_schedules()
    return [
        schedule
        for schedule in schedules
        if schedule.effective_slots
        and str(schedule.TeamName or "").strip().casefold()
        not in _LEGACY_PLACEHOLDER_TEAM_NAMES
    ]


def _raid_schedule_card(self, _build=None) -> FoundryCard:
    card = FoundryCard("Raid Schedule")
    card.addWidget(self._section_label("SAVED TEAM SCHEDULES"))

    try:
        schedules = _saved_schedules()
    except Exception as exc:
        message = QLabel(f"Saved schedules unavailable.\n{exc}")
        message.setWordWrap(True)
        message.setProperty("muted", True)
        card.addWidget(message)
        card.addStretch(1)
        card.addWidget(self._compact_button("Open Calendar"))
        return card

    if not schedules:
        empty = QLabel("No team raid times are saved yet.")
        empty.setWordWrap(True)
        empty.setProperty("muted", True)
        card.addWidget(empty)
    else:
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        for row, schedule in enumerate(schedules[:6]):
            team = QLabel(schedule.TeamName)
            team.setProperty("overviewGoalName", True)
            grid.addWidget(team, row, 0)

            slots = list(schedule.effective_slots)
            day_text = "\n".join(slot.Day for slot in slots)
            days = QLabel(day_text)
            days.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(days, row, 1)

            time_lines = []
            for slot in slots:
                if slot.EndTime:
                    time_lines.append(f"{slot.StartTime}–{slot.EndTime}")
                else:
                    time_lines.append(slot.StartTime)
            if schedule.TimeZone and time_lines:
                time_lines[-1] = f"{time_lines[-1]}\n{schedule.TimeZone}"
            when = QLabel("\n".join(time_lines))
            when.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            when.setProperty("muted", True)
            grid.addWidget(when, row, 2)

        card.addLayout(grid)
        if len(schedules) > 6:
            more = QLabel(f"+ {len(schedules) - 6} more scheduled team(s)")
            more.setProperty("muted", True)
            card.addWidget(more)

    card.addStretch(1)
    card.addWidget(self._compact_button("Open Calendar"))
    return card


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import operations_console
    from ui.team_schedule_calendar_support import install as install_team_schedule_calendar_support
    from ui.team_schedule_multi_time_support import install as install_team_schedule_multi_time_support
    from ui.roster_player_architecture_support import install as install_roster_player_architecture_support

    # Preserve the portable calendar feature, then let the multi-time layer own
    # the final Team Schedule UI so each selected day can use its own start/end.
    install_team_schedule_calendar_support()
    install_team_schedule_multi_time_support()
    # Characters and Teams compose the canonical build catalog with the durable
    # roster/team schedule state after the final Team Schedule patch is known.
    install_roster_player_architecture_support()
    operations_console.OperationsConsole._raid_schedule_card = _raid_schedule_card
    _INSTALLED = True
