from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem

from engine.config import get_data_dir
from services.team_prescription import (
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_slot_constraints import project_slot_build_constraints
from services.team_prescription_template_sources import apply_team_template_sources


_INSTALLED = False
_ORIGINAL_GENERATE = None
_ORIGINAL_SCOPE = None


def _complete_prescription_scope(self) -> TeamPrescriptionScope:
    """Honor existing locks while allowing a truly complete build prescription."""

    assert _ORIGINAL_SCOPE is not None
    original = _ORIGINAL_SCOPE(self)
    dimensions = list(original.dimensions)
    if not self.constraint_boxes["Keep Current Builds"].isChecked():
        for dimension in (
            PrescriptionDimension.RACE,
            PrescriptionDimension.SKILLS,
            PrescriptionDimension.MORPHS,
            PrescriptionDimension.CHAMPION_POINTS,
            PrescriptionDimension.MUNDUS,
            PrescriptionDimension.FOOD,
            PrescriptionDimension.POTION,
        ):
            if dimension not in dimensions:
                dimensions.append(dimension)
    return TeamPrescriptionScope(dimensions=tuple(dimensions))


def _ensure_template_base(page) -> None:
    """Create an honest open-chair base when Hybrid has no saved players yet."""

    if page.current_prescription is not None:
        return
    if page._effective_source_mode() != "Hybrid: Players + Recruitment":
        return
    goal = page.goal_combo.currentText().strip() or "Custom Goal"
    base = generate_prescribed_roster_from_saved_builds(
        name=f"{goal} Prescribed Roster",
        goal=goal,
        slot_labels=tuple(page._role_slots()),
        builds=(),
        scope=page._prescription_scope(),
    )
    build_constraints = page._prescription_build_constraints()
    page.current_prescription = project_slot_build_constraints(
        roster=base,
        constraints=tuple(build_constraints.values()),
    )


def _needs_template_candidates(page) -> bool:
    if page._effective_source_mode() == "Saved Players Only":
        return False
    prescription = page.current_prescription
    if prescription is None:
        return False
    return any(
        assignment.is_open_for_candidate
        for assignment in prescription.assignments
    )


def _change_value(assignment, dimension: PrescriptionDimension) -> str:
    change = assignment.change_for(dimension)
    return "" if change is None else str(change.prescribed_value or "").strip()


def _change_reason(assignment) -> str:
    for change in assignment.changes:
        reason = str(change.reason or "").strip()
        if reason:
            return reason
    return "Template evidence; complete build fields remain unresolved."


def _partial_template_assignments(roster) -> tuple:
    return tuple(
        assignment
        for assignment in roster.assignments
        if assignment.player_name is None
        and assignment.prescribed_build is None
        and assignment.has_candidate_recommendation
    )


def _append_partial_template_rows(page, roster) -> None:
    partial = _partial_template_assignments(roster)
    if not partial:
        return

    gear_placeholder = (
        page.gear_table.rowCount() == 1
        and page.gear_table.item(0, 0) is not None
        and page.gear_table.item(0, 0).text() == "—"
    )
    skill_placeholder = (
        page.skill_table.rowCount() == 1
        and page.skill_table.item(0, 0) is not None
        and page.skill_table.item(0, 0).text() == "—"
    )
    if gear_placeholder:
        page.gear_table.setRowCount(0)
    if skill_placeholder:
        page.skill_table.setRowCount(0)

    for assignment in partial:
        class_name = _change_value(assignment, PrescriptionDimension.CLASS)
        build_name = _change_value(assignment, PrescriptionDimension.BUILD)
        gear = _change_value(assignment, PrescriptionDimension.GEAR)
        skills = _change_value(assignment, PrescriptionDimension.SKILLS)
        mundus = _change_value(assignment, PrescriptionDimension.MUNDUS)
        reason = _change_reason(assignment)
        subject = assignment.slot_name

        gear_bits = [value for value in (gear, build_name, class_name, mundus) if value]
        gear_row = page.gear_table.rowCount()
        page.gear_table.insertRow(gear_row)
        for column, value in enumerate(
            (
                subject,
                " | ".join(gear_bits) if gear_bits else "Partial template setup",
                reason,
            )
        ):
            page.gear_table.setItem(gear_row, column, QTableWidgetItem(str(value)))

        skill_row = page.skill_table.rowCount()
        page.skill_table.insertRow(skill_row)
        unresolved = "; ".join(assignment.unresolved) or "—"
        for column, value in enumerate(
            (
                subject,
                skills or "No known skills in template",
                "—",
                f"{reason} Unresolved: {unresolved}" if unresolved != "—" else reason,
            )
        ):
            page.skill_table.setItem(skill_row, column, QTableWidgetItem(str(value)))


def _generate_prescription_with_templates(self, *args):
    """Run saved-player prescription first, then fill remaining chairs from templates."""

    assert _ORIGINAL_GENERATE is not None
    _ORIGINAL_GENERATE(self, *args)
    _ensure_template_base(self)
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
    _append_partial_template_rows(self, result.final_roster)
    complete_count = sum(
        1
        for assignment in result.final_roster.assignments
        if assignment.prescribed_build is not None and assignment.player_name is None
    )
    partial_count = len(_partial_template_assignments(result.final_roster))
    open_count = sum(
        1
        for assignment in result.final_roster.assignments
        if assignment.is_open_for_candidate
    )
    message = (
        f"Template pass applied {result.applied_count} recommendation(s): "
        f"{complete_count} complete template build(s), {partial_count} partial template "
        f"setup(s), {open_count} chair(s) still open. Local sources available: "
        f"{result.published_template_count} published + "
        f"{result.observed_template_count} observed."
    )
    if partial_count or open_count or result.unresolved:
        self.status.warning(message)
    else:
        self.status.success(message)


def install() -> None:
    global _INSTALLED, _ORIGINAL_GENERATE, _ORIGINAL_SCOPE
    if _INSTALLED:
        return
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_GENERATE = OptimizationPage._generate_prescription_preview
    _ORIGINAL_SCOPE = OptimizationPage._prescription_scope
    OptimizationPage._prescription_scope = _complete_prescription_scope
    OptimizationPage._generate_prescription_preview = _generate_prescription_with_templates
    _INSTALLED = True

    # Keep the recruit selector honest (there is still no human assigned) while
    # decorating its remaining columns with the template BFF actually prescribed.
    from ui.team_prescription_row_display_support import install as install_row_display

    install_row_display()
