from __future__ import annotations

from engine.config import get_data_dir
from services.team_prescription_template_sources import apply_team_template_sources


_INSTALLED = False
_ORIGINAL_GENERATE = None


def _needs_template_candidates(page) -> bool:
    if page._effective_source_mode() == "Saved Players Only":
        return False
    prescription = page.current_prescription
    if prescription is None:
        return False
    return any(
        assignment.player_name is None
        and assignment.prescribed_build is None
        and not assignment.changes
        for assignment in prescription.assignments
    )


def _generate_prescription_with_templates(self, *args):
    """Run saved-player prescription first, then fill remaining chairs from templates."""

    assert _ORIGINAL_GENERATE is not None
    _ORIGINAL_GENERATE(self, *args)
    if not _needs_template_candidates(self):
        return

    from ui.team_prescription_pipeline_support import _finalize_prescription_ui

    goal = self.goal_combo.currentText().strip() or "Custom Goal"
    build_constraints = self._prescription_build_constraints()
    try:
        result = apply_team_template_sources(
            roster=self.current_prescription,
            goal=goal,
            data_dir=get_data_dir(),
            build_constraints_by_slot=build_constraints,
        )
    except Exception as exc:
        self.status.error(f"Team template candidates could not be evaluated: {exc}")
        return

    if result.applied_count <= 0:
        # No local template source could improve the open chairs. Preserve the
        # saved-player/recruitment status text produced by the authoritative first pass.
        return

    _finalize_prescription_ui(self, result.final_roster)
    complete_count = sum(
        1
        for assignment in result.final_roster.assignments
        if assignment.prescribed_build is not None and assignment.player_name is None
    )
    partial_count = sum(
        1
        for assignment in result.final_roster.assignments
        if assignment.player_name is None
        and assignment.prescribed_build is None
        and bool(assignment.changes)
    )
    open_count = sum(
        1
        for assignment in result.final_roster.assignments
        if assignment.player_name is None
        and assignment.prescribed_build is None
        and not assignment.changes
    )
    message = (
        f"Template pass applied {result.applied_count} recommendation(s): "
        f"{complete_count} complete template build(s), {partial_count} partial observed "
        f"setup(s), {open_count} chair(s) still open. Local sources available: "
        f"{result.published_template_count} published + "
        f"{result.observed_template_count} observed."
    )
    if partial_count or open_count or result.unresolved:
        self.status.warning(message)
    else:
        self.status.success(message)


def install() -> None:
    global _INSTALLED, _ORIGINAL_GENERATE
    if _INSTALLED:
        return
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_GENERATE = OptimizationPage._generate_prescription_preview
    OptimizationPage._generate_prescription_preview = _generate_prescription_with_templates
    _INSTALLED = True
