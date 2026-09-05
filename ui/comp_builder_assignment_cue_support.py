from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _details_card(page) -> FoundryCard | None:
    wanted = {
        "Composition Details & Summary",
        "Selected Chair Setup & Evidence",
        "ESO Logs Catalog & Chair Evidence",
    }
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() in wanted:
            return card
    return None


def _selected_row(page) -> int:
    row = page.matrix_table.currentRow()
    if row >= 0:
        return row
    return 0 if page.matrix_table.rowCount() else -1


def _assignment_text(page) -> str:
    row = _selected_row(page)
    if row < 0:
        return "← SELECT A PLAYER / CHAIR ON THE LEFT"

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1) or "Unresolved role"
    selected_class = page._selected_class(row) or "Any class"

    candidate_name = "Top eligible build"
    try:
        from ui import comp_builder_build_candidate_support as candidate_support

        candidates = candidate_support._chair_candidates(page, row)
        if candidates:
            candidate_name = candidates[0].name
    except (OSError, ValueError):
        pass

    return (
        f"{candidate_name}  ←  ASSIGN TO {slot_name}\n"
        f"{role} • {selected_class}"
    )


def _refresh_assignment_cue(page) -> None:
    cue = getattr(page, "comp_assignment_cue_label", None)
    if cue is not None:
        cue.setText(_assignment_text(page))


def _install_assignment_cue(page) -> None:
    # The selected matrix row and the source-build block share one accent treatment.
    # This is a visual relationship only; assignment still uses the existing tested
    # candidate application path.
    page.matrix_table.setProperty("compAssignmentTarget", True)

    candidate_label = getattr(page, "comp_build_candidates_label", None)
    if candidate_label is not None:
        candidate_label.setProperty("compAssignmentSource", True)

    details = _details_card(page)
    if details is not None:
        details.setProperty("compAssignmentSourceCard", True)
        scroll = next(iter(details.findChildren(QScrollArea)), None)
        body = scroll.widget() if scroll is not None else None
        layout = body.layout() if body is not None else None
        if layout is not None:
            cue = QLabel()
            cue.setWordWrap(True)
            cue.setProperty("compAssignmentCue", True)
            candidate_index = (
                layout.indexOf(candidate_label)
                if candidate_label is not None
                else -1
            )
            insert_at = candidate_index if candidate_index >= 0 else 0
            layout.insertWidget(insert_at, cue)
            page.comp_assignment_cue_label = cue

    page.matrix_table.currentCellChanged.connect(
        lambda *_args: _refresh_assignment_cue(page)
    )
    page.goal_combo.currentTextChanged.connect(
        lambda *_args: _refresh_assignment_cue(page)
    )
    _refresh_assignment_cue(page)


def _comp_init_with_assignment_cue(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_assignment_cue(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_assignment_cue
    _INSTALLED = True
