from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QScrollArea

from models.build_model import PlayerBuild
from services.comp_builder_build_candidates import CompBuildCandidate
from services.team_prescription_slot_constraints import (
    PrescribedSlotBuildConstraint,
    parse_required_gear_sets,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_CHAIR_CANDIDATES = None
_ORIGINAL_RENDER_SLOTS = None
_ORIGINAL_SEND_TO_ROSTER = None


def _candidate_fact_build(candidate: CompBuildCandidate) -> PlayerBuild:
    armor = {
        f"ConstraintEvidence{index}": {"Set": name}
        for index, name in enumerate(candidate.gear_sets)
    }
    return PlayerBuild(
        EsoClass=candidate.eso_class,
        Role=candidate.role,
        Armor=armor,
    )


def candidate_matches_constraint(
    candidate: CompBuildCandidate,
    constraint: PrescribedSlotBuildConstraint,
) -> bool:
    """Evaluate exact candidate facts through the existing hard-constraint model."""

    return constraint.matches(_candidate_fact_build(candidate))


def _slot_name(page, row: int) -> str:
    return page._cell_text(row, 0) or f"Slot {row + 1}"


def _constraint_for_row(page, row: int) -> PrescribedSlotBuildConstraint | None:
    if row < 0 or row >= page.matrix_table.rowCount():
        return None
    slot_name = _slot_name(page, row)
    selected_class = page._selected_class(row).strip()
    required_class = None if selected_class.casefold() == "any class" else selected_class
    gear_sets = tuple(
        getattr(page, "_comp_required_gear_sets_by_slot", {}).get(slot_name, ())
    )
    if not required_class and not gear_sets:
        return None
    return PrescribedSlotBuildConstraint(
        slot_name=slot_name,
        required_class=required_class,
        required_gear_sets=gear_sets,
    )


def _chair_candidates_with_build_constraints(page, row: int):
    assert _ORIGINAL_CHAIR_CANDIDATES is not None
    candidates = tuple(_ORIGINAL_CHAIR_CANDIDATES(page, row))
    constraint = _constraint_for_row(page, row)
    if constraint is None:
        return candidates
    return tuple(
        candidate
        for candidate in candidates
        if candidate_matches_constraint(candidate, constraint)
    )


def _selected_row(page) -> int:
    from ui import comp_builder_build_candidate_support as support

    return support._selected_row(page)


def _sync_constraint_editor(page) -> None:
    editor = getattr(page, "comp_required_gear_sets_input", None)
    if editor is None:
        return
    row = _selected_row(page)
    value = ""
    if row >= 0:
        slot_name = _slot_name(page, row)
        value = ", ".join(
            getattr(page, "_comp_required_gear_sets_by_slot", {}).get(slot_name, ())
        )
    editor.blockSignals(True)
    editor.setText(value)
    editor.blockSignals(False)


def _constraint_text_changed(page, text: str) -> None:
    from ui import comp_builder_build_candidate_support as support

    row = _selected_row(page)
    if row < 0:
        return
    slot_name = _slot_name(page, row)
    gear_sets = parse_required_gear_sets(text)
    if gear_sets:
        page._comp_required_gear_sets_by_slot[slot_name] = gear_sets
    else:
        page._comp_required_gear_sets_by_slot.pop(slot_name, None)

    applied = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    constraint = _constraint_for_row(page, row)
    if applied is not None and constraint is not None:
        if not candidate_matches_constraint(applied, constraint):
            page._comp_applied_candidates.pop(slot_name, None)
            page.status.warning(
                f"Cleared {applied.name} from {slot_name}: it does not satisfy the "
                "updated hard build ingredients."
            )

    support._refresh_candidates(page)


def _details_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Composition Details & Summary":
            return card
    return None


def _install_constraint_ui(page) -> None:
    page._comp_required_gear_sets_by_slot: dict[str, tuple[str, ...]] = {}
    page.comp_required_gear_sets_label = QLabel("BUILD AROUND • REQUIRED GEAR SETS")
    page.comp_required_gear_sets_input = QLineEdit()
    page.comp_required_gear_sets_input.setPlaceholderText(
        "e.g. Serpent's Disdain, Pillager's Profit"
    )
    page.comp_required_gear_sets_input.textChanged.connect(
        lambda text: _constraint_text_changed(page, text)
    )

    details = _details_card(page)
    if details is not None:
        scroll = next(iter(details.findChildren(QScrollArea)), None)
        body = scroll.widget() if scroll is not None else None
        layout = body.layout() if body is not None else None
        if layout is not None:
            anchor = getattr(page, "apply_comp_candidate_button", None)
            index = layout.indexOf(anchor) if anchor is not None else -1
            insert_at = index if index >= 0 else layout.count()
            layout.insertWidget(insert_at, page.comp_required_gear_sets_label)
            layout.insertWidget(insert_at + 1, page.comp_required_gear_sets_input)
        else:
            details.addWidget(page.comp_required_gear_sets_label)
            details.addWidget(page.comp_required_gear_sets_input)

    page.matrix_table.currentCellChanged.connect(
        lambda *_args: _sync_constraint_editor(page)
    )
    _sync_constraint_editor(page)


def _render_slots_with_constraint_reset(self, slots) -> None:
    assert _ORIGINAL_RENDER_SLOTS is not None
    _ORIGINAL_RENDER_SLOTS(self, slots)
    if hasattr(self, "_comp_required_gear_sets_by_slot"):
        self._comp_required_gear_sets_by_slot.clear()
        _sync_constraint_editor(self)


def _send_to_roster_with_constraint_validation(self, *_args) -> None:
    from ui import comp_builder_build_candidate_support as support

    assert _ORIGINAL_SEND_TO_ROSTER is not None
    applied = getattr(self, "_comp_applied_candidates", {})
    if applied:
        rows_by_slot = {
            _slot_name(self, row): row
            for row in range(self.matrix_table.rowCount())
        }
        for slot_name, candidate in applied.items():
            row = rows_by_slot.get(slot_name)
            if row is None:
                self.status.error(
                    f"Could not transfer optimized team: chair {slot_name!r} no longer exists."
                )
                return
            current_ids = {
                item.candidate_id
                for item in support._chair_candidates(self, row)
            }
            if candidate.candidate_id not in current_ids:
                self.status.error(
                    f"Could not transfer {slot_name}: {candidate.name} no longer satisfies "
                    "the current hard class/gear ingredients. Re-optimize the team first."
                )
                return
    _ORIGINAL_SEND_TO_ROSTER(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_CHAIR_CANDIDATES, _ORIGINAL_RENDER_SLOTS, _ORIGINAL_SEND_TO_ROSTER
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as support
    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_CHAIR_CANDIDATES = support._chair_candidates
    support._chair_candidates = _chair_candidates_with_build_constraints

    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    CompBuilderPage._render_slots = _render_slots_with_constraint_reset

    _ORIGINAL_SEND_TO_ROSTER = CompBuilderPage._send_to_roster
    CompBuilderPage._send_to_roster = _send_to_roster_with_constraint_validation

    original_init = CompBuilderPage.__init__

    def init_with_build_constraints(self, parent=None):
        original_init(self, parent)
        _install_constraint_ui(self)

    CompBuilderPage.__init__ = init_with_build_constraints
    _INSTALLED = True
