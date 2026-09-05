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

    # Install last in the existing team-support chain. The underlying prescription
    # machinery remains available, but its direct composition-building UI is removed
    # from Optimization now that Comp Builder owns that responsibility.
    from ui.team_optimization_role_cleanup import install as install_role_cleanup

    install_role_cleanup()

    # Comp Builder owns the planned coverage scoreboard; the shared progress layer
    # keeps its evidence-driven checkmarks refreshed.
    from ui.team_progress_support import install as install_team_progress_support

    install_team_progress_support()

    # ESO Logs composition evidence is additive: observed snapshots can inform
    # Comp Builder classes without overwriting responsibilities/providers.
    from ui.comp_builder_esologs_support import install as install_comp_builder_esologs

    install_comp_builder_esologs()

    # Keep the selected-chair setup above the all-chair ESO Logs summary so gear and
    # skills are visible immediately when a matrix row is selected.
    from ui.comp_builder_esologs_chair_layout import install as install_comp_builder_esologs_chair_layout

    install_comp_builder_esologs_chair_layout()

    # Merge saved BFF builds with versioned reference templates for the selected
    # composition chair. ESO Logs overlap improves relevance when that evidence is
    # available, but hidden log setup data is never fabricated.
    from ui.comp_builder_build_candidate_support import install as install_comp_builder_build_candidates

    install_comp_builder_build_candidates()

    # Upgrade the all-chair action from greedy row order to one deterministic team
    # assignment. Manual chair choices remain fixed, saved players remain unique,
    # and reference templates stay reusable recruitment evidence.
    from ui.comp_builder_team_candidate_optimizer_support import (
        install as install_comp_builder_team_candidate_optimizer,
    )

    install_comp_builder_team_candidate_optimizer()

    # Materialize those already-selected Comp Maker assignments into the existing
    # PrescribedRoster model before roster transfer. This bridge never reranks; it
    # only resolves the optimizer's authoritative saved/template candidate IDs.
    from ui.comp_builder_authoritative_prescription_support import (
        install as install_comp_builder_authoritative_prescription,
    )

    install_comp_builder_authoritative_prescription()

    # Finally tighten the page geometry. This runs after the additive Comp Builder
    # support modules so Actions stays pinned top-right, coverage sits directly under
    # the matrix, and only the Details card owns flexible vertical space.
    from ui.comp_builder_layout_support import install as install_comp_builder_layout

    install_comp_builder_layout()
