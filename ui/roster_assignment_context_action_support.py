from __future__ import annotations

"""Make Assignments quick actions honor the selected team/boss context."""

from services.build_context_variant_service import resolve_build_context
from ui.roster_encounter_assignment_context_support import (
    selected_encounter_id,
    selected_encounter_name,
)


_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import roster_assignment_action_support as actions

    original_coverage_builds_for_team = actions._coverage_builds_for_team

    def coverage_builds_for_selected_context(page, members):
        selected, unresolved = original_coverage_builds_for_team(page, members)
        team_name = actions._selected_team_name(page)
        boss_name = selected_encounter_name(page)
        resolved = tuple(
            (
                slot,
                resolve_build_context(
                    build,
                    team_name=team_name,
                    boss_name=boss_name,
                ),
            )
            for slot, build in selected
        )
        return resolved, unresolved

    def evaluate_selected_team(page) -> None:
        team_name = actions._selected_team_name(page)
        if not team_name:
            page.status.warning("Choose a team before opening Coverage.")
            return

        if not actions._show_page(page, "console:7"):
            return

        window = page.window()
        coverage = getattr(window, "pages", {}).get("console:7")
        if coverage is None:
            page.status.warning("Coverage could not be opened.")
            return

        coverage.status.info(
            f"{team_name} is a reusable Roster team. Coverage now evaluates saved "
            "trial-specific Raid Plans only; choose the matching Raid Plan above."
        )

    actions._coverage_builds_for_team = coverage_builds_for_selected_context
    # Legacy Roster Assignments may still navigate to Coverage, but they no longer
    # inject a transient Team/Boss scope. The saved Raid Plan is the visible Coverage
    # authority for trial-specific provider evaluation.
    actions._evaluate_team = evaluate_selected_team
    actions._selected_assignment_encounter_id = selected_encounter_id
    actions._selected_assignment_encounter_name = selected_encounter_name
    _INSTALLED = True


__all__ = ["install"]
