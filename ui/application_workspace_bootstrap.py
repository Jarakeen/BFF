from __future__ import annotations

"""Explicit application composition for roster/rotation/build workspace extensions.

This module owns startup ordering for cross-feature UI decorators that must be installed
before ``MainWindow`` construction. Feature modules should install only their own behavior;
application-wide composition belongs here where the order is visible and reviewable.
"""

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.roster_duplicate_player_merge_service import merge_duplicate_roster_players

_BOOTSTRAPPED = False


def bootstrap_workspace_extensions() -> None:
    """Install the roster/rotation/build workspace extension graph exactly once."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

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
    from ui.coverage_capability_gap_visibility_support import install as install_coverage_capability_gap_visibility_support
    from ui.roster_team_assignment_filter_support import install as install_roster_team_assignment_filter_support
    from ui.roster_encounter_assignment_context_support import install as install_roster_encounter_assignment_context_support
    from ui.roster_characters_header_context_support import install as install_roster_characters_header_context_support
    from ui.roster_assignment_persistence_support import install as install_roster_assignment_persistence_support
    from ui.roster_assignment_action_support import install as install_roster_assignment_action_support
    from ui.roster_assignment_context_action_support import install as install_roster_assignment_context_action_support
    from ui.roster_assignment_usability_support import install as install_roster_assignment_usability_support
    from ui.roster_player_alias_support import install as install_roster_player_alias_support
    from ui.comp_builder_roster_intake_support import install as install_comp_builder_roster_intake_support
    from ui.build_context_variant_support import install as install_build_context_variant_support
    from ui.build_reuse_template_support import install as install_build_reuse_template_support
    from ui.phase14_builds_command_center_support import install as install_phase14_builds_command_center_support
    from ui.phase14_build_profile_support import install as install_phase14_build_profile_support
    from ui.phase14_build_inspector_support import install as install_phase14_build_inspector_support
    from ui.phase14_build_lifecycle_guard_support import install as install_phase14_build_lifecycle_guard_support
    from ui.phase14_build_visual_target_support import install as install_phase14_build_visual_target_support
    from ui.phase14_build_icon_polish_support import install as install_phase14_build_icon_polish_support
    from ui.phase14_build_edit_return_support import install as install_phase14_build_edit_return_support
    from ui.phase14_build_focused_editors_support import install as install_phase14_build_focused_editors_support

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
    install_roster_import_identity_resolution_support()
    install_roster_gear_set_alias_import_support()
    install_roster_import_context_variant_support()
    install_roster_import_sparse_alternate_support()
    install_roster_import_match_preview_support()
    install_roster_import_build_confirmation_support()
    install_coverage_capability_gap_visibility_support()
    install_roster_team_assignment_filter_support()
    install_roster_encounter_assignment_context_support()
    install_roster_characters_header_context_support()
    install_roster_assignment_persistence_support()
    install_roster_assignment_action_support()
    install_roster_assignment_context_action_support()
    install_roster_assignment_usability_support()
    install_roster_player_alias_support()
    install_comp_builder_roster_intake_support()
    install_build_context_variant_support()
    install_build_reuse_template_support()
    # Phase 14 layers the command-center shell over existing canonical build behavior,
    # then adds persisted profile defaults/favorite/archive metadata without mutating
    # the saved build or ESO database. The command center itself routes New Build to
    # the existing Easy Mode action, so no second wrapper is needed around _build_ui.
    # The inspector supplies the read-first dossier. The lifecycle guard reconstructs
    # presentation if older wrappers detach it, and the final visual passes align the
    # mockup geometry plus class/role/gear/skill icon vocabulary.
    install_phase14_builds_command_center_support()
    install_phase14_build_profile_support()
    install_phase14_build_inspector_support()
    install_phase14_build_lifecycle_guard_support()
    install_phase14_build_visual_target_support()
    install_phase14_build_icon_polish_support()
    install_phase14_build_edit_return_support()
    install_phase14_build_focused_editors_support()

    _BOOTSTRAPPED = True


__all__ = ["bootstrap_workspace_extensions"]
