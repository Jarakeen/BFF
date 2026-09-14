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
    from services.roster_duplicate_player_merge_service import merge_duplicate_roster_players
    from ui.team_schedule_calendar_support import install as install_team_schedule_calendar_support
    from ui.team_schedule_multi_time_support import install as install_team_schedule_multi_time_support
    from ui.roster_team_merge_support import install as install_roster_team_merge_support
    from ui.roster_team_merge_visibility_support import install as install_roster_team_merge_visibility_support
    from ui.roster_team_merge_layout_fix import install as install_roster_team_merge_layout_fix
    from ui.roster_player_architecture_support import install as install_roster_player_architecture_support
    from ui.scrollable_message_dialog_support import install as install_scrollable_message_dialog_support
    from ui.roster_import_workflow import install as install_roster_import_support
    from ui.roster_import_identity_resolution_support import install as install_roster_import_identity_resolution_support
    from ui.roster_gear_set_alias_import_support import install as install_roster_gear_set_alias_import_support
    from ui.roster_import_context_variant_support import install as install_roster_import_context_variant_support
    from ui.roster_import_sparse_alternate_support import install as install_roster_import_sparse_alternate_support
    from ui.roster_import_match_preview_support import install as install_roster_import_match_preview_support
    from ui.roster_import_build_confirmation_support import install as install_roster_import_build_confirmation_support
    from ui.player_build_navigation_support import install as install_player_build_navigation_support
    from ui.rotation_dashboard_layout_support import install as install_rotation_dashboard_layout_support
    from ui.build_rotation_artifact_support import install as install_build_rotation_artifact_support
    from ui.rotation_navigation_refresh_support import install as install_rotation_navigation_refresh_support
    from ui.user_workspace_polish_support import install as install_user_workspace_polish_support
    from ui.roster_team_assignment_filter_support import install as install_roster_team_assignment_filter_support
    from ui.roster_encounter_assignment_context_support import install as install_roster_encounter_assignment_context_support
    from ui.roster_characters_header_context_support import install as install_roster_characters_header_context_support
    from ui.roster_sub_terminology_support import install as install_roster_sub_terminology_support
    from ui.roster_assignment_persistence_support import install as install_roster_assignment_persistence_support
    from ui.roster_assignment_action_support import install as install_roster_assignment_action_support
    from ui.roster_assignment_context_action_support import install as install_roster_assignment_context_action_support
    from ui.roster_assignment_usability_support import install as install_roster_assignment_usability_support
    from ui.roster_player_alias_support import install as install_roster_player_alias_support
    from ui.comp_builder_roster_intake_support import install as install_comp_builder_roster_intake_support
    from ui.build_context_variant_support import install as install_build_context_variant_support
    from ui.build_reuse_template_support import install as install_build_reuse_template_support

    # Personnel is player-level identity. Repair duplicates left by older imports
    # before any roster page reads them. The merge unions teams and moves legacy
    # plus Team/Boss assignments before deleting only the redundant Personnel row.
    merge_duplicate_roster_players(EsoDatabase(get_data_dir() / "eso.db"))

    install_team_schedule_calendar_support()
    install_team_schedule_multi_time_support()
    install_scrollable_message_dialog_support()
    install_roster_team_merge_support()
    install_roster_team_merge_visibility_support()
    install_roster_team_merge_layout_fix()
    install_roster_player_architecture_support()
    install_roster_import_support()
    # Workbooks often omit character names and use gamertags without the leading
    # @ stored by FoundryDock. Resolve equivalent existing identities before the
    # preview asks the user to do anything manually.
    install_roster_import_identity_resolution_support()
    # Normalize roster shorthand such as RO/Pill/SoB/LE/Oz through the canonical
    # gear-set table, preferring Perfected variants when one exists. This layer
    # also repairs recognized shorthand left behind by older imports.
    install_roster_gear_set_alias_import_support()
    # Re-importing a team replaces only that team's prior imported builds for the
    # selected players, then folds boss/loadout columns into sparse Context Variants.
    # Personnel's current character is preferred over historical accidental toons.
    install_roster_import_context_variant_support()
    # Human alternate columns routinely omit unchanged attributes, skills, CP,
    # food, Mundus, and similar values. Treat those blanks as inheritance and
    # separate mixed class/role families before Context Variant consolidation.
    install_roster_import_sparse_alternate_support()
    # The preview should make repeat imports obvious: existing identities are
    # reused, while new characters/builds and genuinely ambiguous rows are labeled.
    install_roster_import_match_preview_support()
    # Workbooks can contain useful-but-ambiguous potion choices and partial scribed
    # recipe rows. Preserve that evidence and make the raid lead explicitly confirm
    # anything Foundry cannot safely promote into canonical build state.
    install_roster_import_build_confirmation_support()
    install_player_build_navigation_support()
    install_rotation_dashboard_layout_support()
    install_build_rotation_artifact_support()
    # Rotations is a long-lived page. Re-entering it after Build edits/imports
    # reloads canonical saved-build state instead of holding startup-era objects.
    install_rotation_navigation_refresh_support()
    install_user_workspace_polish_support()
    install_roster_team_assignment_filter_support()
    # One simple Boss selector sits beside the team selector. Team Default stays
    # the normal path; users only touch Boss when somebody's job changes.
    install_roster_encounter_assignment_context_support()
    install_roster_characters_header_context_support()
    install_roster_sub_terminology_support()
    # Persistence installs after both selectors so it can save team defaults and
    # optional per-boss overrides without asking the user to understand the model.
    install_roster_assignment_persistence_support()
    install_roster_assignment_action_support()
    # Coverage and other quick actions use the same selected Team/Boss context,
    # including the effective build variant, instead of silently scanning base builds.
    install_roster_assignment_context_action_support()
    # Header sorting and the searchable reviewed boss selector install after the
    # assignment layers so they decorate the final table rather than competing with it.
    install_roster_assignment_usability_support()
    # Install player aliases after all other Roster UI decorators so Personnel gets
    # one final merge/alias surface and rename collisions cannot crash refresh.
    install_roster_player_alias_support()
    # Install after the Assignments action layer so its Send to Comp Maker button
    # can hand over actual player/class/role context and the action card can lose
    # the redundant header without creating another parallel workflow.
    install_comp_builder_roster_intake_support()
    # The build editor's old boss-only alternate surface is generalized last so
    # all normal BuildEditor constructors now expose Team / Boss / Team+Boss variants.
    install_build_context_variant_support()
    # Build reuse belongs on the Builds page above the editor. Install after the
    # variant layer so copies and templates preserve the final canonical model.
    install_build_reuse_template_support()
    operations_console.OperationsConsole._raid_schedule_card = _raid_schedule_card
    _INSTALLED = True
