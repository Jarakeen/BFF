from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_APPLY_TOP = None


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


def _selected_candidate(page):
    from ui import comp_builder_build_candidate_support as candidate_support

    row = _selected_row(page)
    if row < 0:
        return None
    try:
        candidates = candidate_support._chair_candidates(page, row)
    except (OSError, ValueError):
        return None

    combo = getattr(page, "comp_candidate_choice_combo", None)
    candidate_id = combo.currentData() if combo is not None else None
    if candidate_id:
        for candidate in candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
    return candidates[0] if candidates else None


def _refresh_picker(page) -> None:
    from ui import comp_builder_build_candidate_support as candidate_support

    combo = getattr(page, "comp_candidate_choice_combo", None)
    if combo is None:
        return

    prior_id = combo.currentData()
    row = _selected_row(page)
    try:
        candidates = candidate_support._chair_candidates(page, row) if row >= 0 else ()
    except (OSError, ValueError):
        candidates = ()

    combo.blockSignals(True)
    combo.clear()
    for rank, candidate in enumerate(candidates, start=1):
        source = "Roster" if candidate.source_kind == "saved_build" else "Reference"
        combo.addItem(
            f"#{rank}  {candidate.name}  •  {source}  •  {candidate.score:.1f}",
            candidate.candidate_id,
        )
    if prior_id:
        index = combo.findData(prior_id)
        if index >= 0:
            combo.setCurrentIndex(index)
    combo.setEnabled(bool(candidates))
    combo.blockSignals(False)

    label = getattr(page, "comp_candidate_choice_label", None)
    if label is not None:
        if candidates:
            label.setText("BUILD CHOICE • Select the build to assign to the highlighted player/chair")
        else:
            label.setText("BUILD CHOICE • No eligible build is available for this player/chair")

    try:
        from ui import comp_builder_assignment_cue_support as cue_support

        cue_support._refresh_assignment_cue(page)
    except (ImportError, AttributeError):
        pass


def _apply_selected_candidate(page, *_args) -> None:
    from ui import comp_builder_build_candidate_support as candidate_support

    row = _selected_row(page)
    if row < 0:
        page.status.warning("Select a player/chair before assigning a build.")
        return

    candidate = _selected_candidate(page)
    if candidate is None:
        page.status.warning("No eligible build is selected for this player/chair.")
        return

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    used_saved_players = candidate_support._used_saved_players(page)
    existing = page._comp_applied_candidates.get(slot_name)
    if existing is not None:
        existing_key = candidate_support._saved_player_key(existing)
        if existing_key:
            used_saved_players.discard(existing_key)

    player_key = candidate_support._saved_player_key(candidate)
    if player_key and player_key in used_saved_players:
        page.status.warning(
            f"{candidate.name} belongs to a saved player already assigned to another chair."
        )
        return

    candidate_support._set_candidate_for_row(page, row, candidate)
    status = "complete build" if candidate.complete_build else "partial build evidence"
    page.status.success(
        f"Assigned {candidate.name} to {slot_name} as {status}. "
        "Send to Roster will preserve this exact build choice."
    )
    candidate_support._refresh_candidates(page)
    _refresh_picker(page)


def _install_picker(page) -> None:
    details = _details_card(page)
    if details is None:
        return

    # Keep the interactive picker outside the long evidence scroll. The ESO Logs
    # catalog may be many screens tall, but choosing a build must remain visible.
    picker_host = QWidget()
    picker_host.setProperty("compCandidatePickerHost", True)
    picker_layout = QVBoxLayout(picker_host)
    picker_layout.setContentsMargins(0, 0, 0, 4)
    picker_layout.setSpacing(4)
    page.comp_candidate_picker_host = picker_host

    page.comp_candidate_choice_label = QLabel()
    page.comp_candidate_choice_label.setWordWrap(True)
    page.comp_candidate_choice_label.setProperty("compCandidateChoiceLabel", True)

    page.comp_candidate_choice_combo = QComboBox()
    page.comp_candidate_choice_combo.setProperty("compCandidateChoice", True)
    page.comp_candidate_choice_combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    page.comp_candidate_choice_combo.setMinimumContentsLength(28)
    page.comp_candidate_choice_combo.currentIndexChanged.connect(
        lambda *_args: _refresh_picker(page)
    )

    picker_layout.addWidget(page.comp_candidate_choice_label)
    picker_layout.addWidget(page.comp_candidate_choice_combo)
    details.body_layout.insertWidget(0, picker_host)

    page.matrix_table.currentCellChanged.connect(lambda *_args: _refresh_picker(page))
    page.goal_combo.currentTextChanged.connect(lambda *_args: _refresh_picker(page))
    if hasattr(page, "refresh_esologs_button"):
        page.refresh_esologs_button.clicked.connect(lambda *_args: _refresh_picker(page))
    if hasattr(page, "apply_esologs_button"):
        page.apply_esologs_button.clicked.connect(lambda *_args: _refresh_picker(page))

    _refresh_picker(page)


def _comp_init_with_candidate_picker(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_picker(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_APPLY_TOP
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as candidate_support
    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_APPLY_TOP = candidate_support._apply_top_candidate
    candidate_support._apply_top_candidate = _apply_selected_candidate

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_candidate_picker
    _INSTALLED = True
