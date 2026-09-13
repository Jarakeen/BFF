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

    # Preserve the portable calendar feature, then let the multi-time layer own
    # the final Team Schedule UI so each selected day can use its own start/end.
    install_team_schedule_calendar_support()
    install_team_schedule_multi_time_support()
    # Long diagnostics must remain readable before workflows start opening
    # warning/information message boxes.
    install_scrollable_message_dialog_support()
    # Team merge wraps the completed Team Schedule surface, so duplicate or
    # renamed team identities can be consolidated without deleting user-owned
    # players, characters, or builds.
    install_roster_team_merge_support()
    # Ensure a visible merge control exists on the completed Teams card.
    install_roster_team_merge_visibility_support()
    # FoundryCard nests the actual action row inside body_layout. Relocate the
    # existing merge control into that concrete row beside Delete Selected Team
    # instead of leaving it as a full-width card strip.
    install_roster_team_merge_layout_fix()
    # Characters and Teams compose the canonical build catalog with the durable
    # roster/team schedule state after the final Team Schedule patch is known.
    install_roster_player_architecture_support()
    # The roster importer then attaches its preview/commit workflow to the
    # existing Import Roster button and reuses canonical roster/build identity.
    install_roster_import_support()
    # Personnel records can jump directly into the selected player's build
    # library only after the final Roster/Builds classes have been composed.
    install_player_build_navigation_support()
    # Rotation layout polish moves the existing canonical controls into their
    # logical cards without replacing or duplicating the mechanics-owned widgets.
    install_rotation_dashboard_layout_support()
    # A completed RotationPlan can then be persisted against the canonical
    # build_id and surfaced as a conditional Build workspace tab.
    install_build_rotation_artifact_support()
    # Final user-facing polish depends on the completed Rotation/Roster/Main
    # composition above, so install it last.
    install_user_workspace_polish_support()
    # Team cards can now scope Assignments after all roster composition layers
    # have installed, without owning or duplicating team membership state.
    install_roster_team_assignment_filter_support()
    # Characters has its own search/tree controls, so assignment-oriented header
    # filters stay visible elsewhere but get out of the way on that tab.
    install_roster_characters_header_context_support()
    # Raid teams use "Sub" terminology; retain compatibility with any legacy
    # records that were persisted before the rename from "Bench".
    install_roster_sub_terminology_support()
    # Assignment edits are durable roster-owned planning state. Install this last
    # so it wraps the final team-filtered Assignments population path.
    install_roster_assignment_persistence_support()
    operations_console.OperationsConsole._raid_schedule_card = _raid_schedule_card
    _INSTALLED = True
