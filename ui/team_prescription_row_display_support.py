from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem

from services.team_prescription import PrescriptionDimension
from services.team_prescription_slot_constraints import build_gear_set_names


_INSTALLED = False
_ORIGINAL_FINALIZE = None


def _change_value(assignment, dimension: PrescriptionDimension) -> str:
    change = assignment.change_for(dimension)
    return "" if change is None else str(change.prescribed_value or "").strip()


def prescribed_recruit_row_values(assignment) -> tuple[str, str, str, str] | None:
    """Return CLASS/BUILD/RESPONSIBILITIES/STATUS for a prescribed recruit chair."""

    if assignment.player_name is not None or not assignment.has_candidate_recommendation:
        return None

    build = assignment.prescribed_build
    if build is not None:
        class_name = str(build.EsoClass or "").strip() or "Flexible"
        build_name = (
            str(assignment.source_build_name or "").strip()
            or str(build.BuildName or "").strip()
            or "Prescribed Build"
        )
        sets = build_gear_set_names(build)
        responsibilities = "Complete prescribed build ready for a compatible recruit"
        if sets:
            responsibilities += ": " + " + ".join(sets)
        return class_name, build_name, responsibilities, "PRESCRIBED"

    class_name = _change_value(assignment, PrescriptionDimension.CLASS) or "Flexible"
    build_name = (
        str(assignment.source_build_name or "").strip()
        or _change_value(assignment, PrescriptionDimension.BUILD)
        or "Partial Template"
    )
    detail_parts: list[str] = []
    gear = _change_value(assignment, PrescriptionDimension.GEAR)
    skills = _change_value(assignment, PrescriptionDimension.SKILLS)
    mundus = _change_value(assignment, PrescriptionDimension.MUNDUS)
    if gear:
        detail_parts.append("Gear: " + gear)
    if skills:
        detail_parts.append("Skills: " + skills)
    if mundus:
        detail_parts.append("Mundus: " + mundus)
    if assignment.unresolved:
        detail_parts.append(f"{len(assignment.unresolved)} unresolved field(s)")
    responsibilities = "; ".join(detail_parts) or "Partial template requirements"
    return class_name, build_name, responsibilities, "TEMPLATE"


def _decorate_team_rows(page, prescription) -> None:
    table = page.team_table
    for row, assignment in enumerate(prescription.assignments):
        values = prescribed_recruit_row_values(assignment)
        if values is None:
            continue
        for column, value in enumerate(values, start=2):
            table.setItem(row, column, QTableWidgetItem(str(value)))


def _finalize_with_prescribed_recruit_rows(page, prescription) -> None:
    assert _ORIGINAL_FINALIZE is not None
    _ORIGINAL_FINALIZE(page, prescription)
    _decorate_team_rows(page, prescription)


def install() -> None:
    global _INSTALLED, _ORIGINAL_FINALIZE
    if _INSTALLED:
        return

    import ui.team_prescription_pipeline_support as pipeline_support

    _ORIGINAL_FINALIZE = pipeline_support._finalize_prescription_ui
    pipeline_support._finalize_prescription_ui = _finalize_with_prescribed_recruit_rows
    _INSTALLED = True
