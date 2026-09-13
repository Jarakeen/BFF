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
    from ui.roster_team_merge_support import install as install_roster_team_merge_support
    from ui.roster_team_merge_visibility_support import install as install_roster_team_merge_visibility_support
    from ui.roster_team_merge_layout_fix import install as install_roster_team_merge_layout_fix
    from ui.roster_player_architecture_support import install as install_roster_player_architecture_support
    from ui.scrollable_message_dialog_support import install as install_scrollable_message_dialog_support
    from ui.roster_import_workflow import install as install_roster_import_support
    from ui.player_build_navigation_support import install as install_player_build_navigation_support
    from ui.rotation_dashboard_layout_support import install as install_rotation_dashboard_layout_support
    from ui.build_rotation_artifact_support import install as install_build_rotation_artifact_support
    from ui.user_workspace_polish_support import install as install_user_workspace_polish_support
    from ui.roster_team_assignment_filter_support import install as install_roster_team_assignment_filter_support
    from ui.roster_characters_header_context_support import install as install_roster_characters_header_context_support
    from ui.roster_sub_terminology_support import install as install_roster_sub_terminology_support
    from ui.roster_assignment_persistence_support import install as install_roster_assignment_persistence_support
    from ui.roster_assignment_action_support import install as install_roster_assignment_action_support
    from ui.comp_builder_roster_intake_support import install as install_comp_builder_roster_intake_support

    install_team_schedule_calendar_support()
    install_team_schedule_multi_time_support()
    install_scrollable_message_dialog_support()
    install_roster_team_merge_support()
    install_roster_team_merge_visibility_support()
    install_roster_team_merge_layout_fix()
    install_roster_player_architecture_support()
    install_roster_import_support()
    install_player_build_navigation_support()
    install_rotation_dashboard_layout_support()
    install_build_rotation_artifact_support()
    install_user_workspace_polish_support()
    install_roster_team_assignment_filter_support()
    install_roster_characters_header_context_support()
    install_roster_sub_terminology_support()
    install_roster_assignment_persistence_support()
    install_roster_assignment_action_support()
    # Install after the Assignments action layer so its Send to Comp Maker button
    # can hand over actual player/class/role context and the action card can lose
    # the redundant header without creating another parallel workflow.
    install_comp_builder_roster_intake_support()
    operations_console.OperationsConsole._raid_schedule_card = _raid_schedule_card
    _INSTALLED = True
