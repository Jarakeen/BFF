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

    actions._coverage_builds_for_team = coverage_builds_for_selected_context
    actions._selected_assignment_encounter_id = selected_encounter_id
    actions._selected_assignment_encounter_name = selected_encounter_name
    _INSTALLED = True


__all__ = ["install"]
