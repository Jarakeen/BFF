from __future__ import annotations


_INSTALLED = False
_ORIGINAL_GENERATE = None


def should_auto_anchor_hybrid_players(
    *,
    source_mode: str,
    saved_player_count: int,
    recruitment_count: int,
    explicit_lock_players: bool,
) -> bool:
    """Never turn Lock Players on implicitly during Generate Best Team.

    The visible Hybrid editor is a working preview, not an invisible lock contract.
    If the user wants exact visible people preserved, the existing Lock Players
    checkbox is the authoritative control. With it unchecked, the prescription
    pipeline may evaluate every eligible saved build and then fill remaining chairs
    from recruitment/template candidates.
    """

    del source_mode, saved_player_count, recruitment_count, explicit_lock_players
    return False


def _generate_with_hybrid_visible_players_preserved(self, *args):
    assert _ORIGINAL_GENERATE is not None
    return _ORIGINAL_GENERATE(self, *args)


def install() -> None:
    global _INSTALLED, _ORIGINAL_GENERATE
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_GENERATE = OptimizationPage._generate_prescription_preview
    OptimizationPage._generate_prescription_preview = (
        _generate_with_hybrid_visible_players_preserved
    )
    _INSTALLED = True

    from ui.team_optimization_role_cleanup import install as install_role_cleanup
    install_role_cleanup()

    from ui.team_progress_support import install as install_team_progress_support
    install_team_progress_support()

    from ui.comp_builder_esologs_support import install as install_comp_builder_esologs
    install_comp_builder_esologs()

    from ui.comp_builder_esologs_chair_layout import install as install_comp_builder_esologs_chair_layout
    install_comp_builder_esologs_chair_layout()

    from ui.comp_builder_build_candidate_support import install as install_comp_builder_build_candidates
    install_comp_builder_build_candidates()

    # Visible style state must exist before the whole-team optimizer is installed.
    from ui.comp_builder_composition_style_support import (
        install as install_comp_builder_composition_style,
    )
    install_comp_builder_composition_style()

    from ui.comp_builder_team_candidate_optimizer_support import (
        install as install_comp_builder_team_candidate_optimizer,
    )
    install_comp_builder_team_candidate_optimizer()

    # Strategy discovery wraps the same authoritative optimizer with canonically
    # proven provider-redistribution novelty; it never creates a second chooser.
    from ui.comp_builder_strategy_support import install as install_comp_builder_strategy
    install_comp_builder_strategy()

    # Comp Maker optimizer choices are authoritative. This materialization does not rerank;
    # it only resolves the already-selected saved/template candidate IDs for roster transfer.
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

    from ui.comp_builder_rylo_support import install as install_comp_builder_rylo
    install_comp_builder_rylo()

    from ui.comp_builder_layout_support import install as install_comp_builder_layout
    install_comp_builder_layout()
