from __future__ import annotations

"""Explicit application composition for Team Optimization and Comp Maker extensions.

This module owns the cross-feature installer order required before MainWindow
construction. Individual feature modules install only their own behavior.
"""


_BOOTSTRAPPED = False


def bootstrap_team_optimization_extensions() -> None:
    """Install the Team Optimization and Comp Maker extension graph exactly once."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    from ui.team_optimization_role_cleanup import install as install_role_cleanup
    install_role_cleanup()

    from ui.team_optimization_canonical_analysis_support import (
        install as install_team_optimization_canonical_analysis,
    )
    install_team_optimization_canonical_analysis()

    from ui.team_progress_support import install as install_team_progress_support
    install_team_progress_support()

    from ui.comp_builder_esologs_support import install as install_comp_builder_esologs
    install_comp_builder_esologs()

    from ui.comp_builder_esologs_chair_layout import install as install_comp_builder_esologs_chair_layout
    install_comp_builder_esologs_chair_layout()

    from ui.comp_builder_build_candidate_support import install as install_comp_builder_build_candidates
    install_comp_builder_build_candidates()

    from ui.comp_builder_candidate_picker_support import (
        install as install_comp_builder_candidate_picker,
    )
    install_comp_builder_candidate_picker()

    from ui.comp_builder_composition_style_support import (
        install as install_comp_builder_composition_style,
    )
    install_comp_builder_composition_style()

    from ui.comp_builder_team_candidate_optimizer_support import (
        install as install_comp_builder_team_candidate_optimizer,
    )
    install_comp_builder_team_candidate_optimizer()

    from ui.comp_builder_strategy_support import install as install_comp_builder_strategy
    install_comp_builder_strategy()

    from ui.comp_builder_authoritative_prescription_support import (
        install as install_comp_builder_authoritative_prescription,
    )
    install_comp_builder_authoritative_prescription()

    from ui.comp_builder_build_constraint_support import (
        install as install_comp_builder_build_constraints,
    )
    install_comp_builder_build_constraints()

    from ui.comp_builder_workspace_support import install as install_comp_builder_workspace
    install_comp_builder_workspace()

    from ui.comp_builder_main_controls_support import (
        install as install_comp_builder_main_controls,
    )
    install_comp_builder_main_controls()

    from ui.comp_builder_assignment_cue_support import (
        install as install_comp_builder_assignment_cue,
    )
    install_comp_builder_assignment_cue()

    from ui.comp_builder_trial_flow_support import (
        install as install_comp_builder_trial_flow,
    )
    install_comp_builder_trial_flow()

    from ui.comp_builder_esologs_snapshot_candidate_support import (
        install as install_comp_builder_esologs_snapshot_candidates,
    )
    install_comp_builder_esologs_snapshot_candidates()

    from ui.comp_builder_final_constraint_guard_support import (
        install as install_comp_builder_final_constraint_guard,
    )
    install_comp_builder_final_constraint_guard()

    from ui.comp_builder_send_feedback_support import (
        install as install_comp_builder_send_feedback,
    )
    install_comp_builder_send_feedback()

    from ui.comp_builder_roster_view_support import (
        install as install_comp_builder_roster_view,
    )
    install_comp_builder_roster_view()

    from ui.roster_template_button_cleanup_support import (
        install as install_roster_template_button_cleanup,
    )
    install_roster_template_button_cleanup()

    from ui.roster_assignment_build_details_support import (
        install as install_roster_assignment_build_details,
    )
    install_roster_assignment_build_details()

    from ui.roster_recruit_adoption_support import (
        install as install_roster_recruit_adoption,
    )
    install_roster_recruit_adoption()

    from ui.roster_recruit_prescription_details_support import (
        install as install_roster_recruit_prescription_details,
    )
    install_roster_recruit_prescription_details()

    from ui.comp_builder_rylo_support import install as install_comp_builder_rylo
    install_comp_builder_rylo()

    from ui.comp_builder_layout_support import install as install_comp_builder_layout
    install_comp_builder_layout()

    from ui.stickerbook_bookmark_support import install as install_stickerbook_bookmarks
    install_stickerbook_bookmarks()

    from ui.gear_lookup_bookmark_support import install as install_gear_lookup_bookmarks
    install_gear_lookup_bookmarks()

    from ui.comp_builder_polish_support import install as install_comp_builder_polish
    install_comp_builder_polish()

    from ui.team_provider_workload_support import (
        install as install_team_provider_workload_support,
    )
    install_team_provider_workload_support()

    from ui.team_provider_saved_rotation_support import (
        install as install_team_provider_saved_rotation_support,
    )
    install_team_provider_saved_rotation_support()

    from ui.coverage_group_effect_catalog_support import (
        install as install_coverage_group_effect_catalog_support,
    )
    install_coverage_group_effect_catalog_support()

    from ui.rotation_tank_provider_scope_transfer_support import (
        install as install_rotation_tank_provider_scope_transfer_support,
    )
    install_rotation_tank_provider_scope_transfer_support()

    _BOOTSTRAPPED = True


__all__ = ["bootstrap_team_optimization_extensions"]
