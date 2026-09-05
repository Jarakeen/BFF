from __future__ import annotations

from engine.config import get_data_dir
from services.comp_builder_authoritative_prescription import (
    CompBuilderAuthoritativePrescriptionService,
)


_INSTALLED = False
_ORIGINAL_SEND_TO_ROSTER = None


def _materialize_current_comp(page):
    applied = getattr(page, "_comp_applied_candidates", {})
    if not applied:
        page._comp_current_prescription = None
        return None

    slots = tuple(
        (
            page._cell_text(row, 0) or f"Slot {row + 1}",
            page._cell_text(row, 1) or "DD",
        )
        for row in range(page.matrix_table.rowCount())
    )
    goal = page.goal_combo.currentText().strip() or "Custom Goal"
    name = page.plan_name_input.text().strip() or f"{goal} Composition"
    prescription = CompBuilderAuthoritativePrescriptionService(get_data_dir()).materialize(
        name=name,
        goal=goal,
        slots=slots,
        candidates_by_slot=dict(applied),
    )
    page._comp_current_prescription = prescription
    return prescription


def _send_to_roster_with_authoritative_prescription(self, *_args) -> None:
    assert _ORIGINAL_SEND_TO_ROSTER is not None
    if getattr(self, "_comp_applied_candidates", {}):
        try:
            _materialize_current_comp(self)
        except (OSError, ValueError) as exc:
            self.status.error(
                "Could not materialize the optimized Comp Maker assignment without "
                f"reranking it: {exc}"
            )
            return
    _ORIGINAL_SEND_TO_ROSTER(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_SEND_TO_ROSTER
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_SEND_TO_ROSTER = CompBuilderPage._send_to_roster
    CompBuilderPage._send_to_roster = _send_to_roster_with_authoritative_prescription
    CompBuilderPage._materialize_authoritative_comp = _materialize_current_comp
    _INSTALLED = True
