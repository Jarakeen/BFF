from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

from services.comp_builder_trial_scope import (
    COMP_MAKER_TRIALS,
    default_goal_for_trial,
    trial_for_selection,
)


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _matching_template_for_selected_trial(self):
    trial_name = trial_for_selection(self.goal_combo.currentText())
    difficulty = self.difficulty_combo.currentText().strip()

    # Trial identity is authoritative in the new UI. Prefer an exact trial-name
    # match, then fall back to the older achievement-keyed catalog identity.
    for template in self.snapshot.templates:
        if template.trial_name.casefold() != trial_name.casefold():
            continue
        if difficulty and template.difficulty and template.difficulty.casefold() != difficulty.casefold():
            continue
        return template

    legacy_goal = default_goal_for_trial(trial_name)
    for template in self.snapshot.templates:
        if template.goal.casefold() != legacy_goal.casefold():
            continue
        if difficulty and template.difficulty and template.difficulty.casefold() != difficulty.casefold():
            continue
        return template
    return None


def _chair_candidates_for_selected_trial(page, row: int):
    if row < 0:
        return ()

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1)
    preferred_class = page._selected_class(row) or "Any class"
    trial_name = trial_for_selection(page.goal_combo.currentText())
    goal = default_goal_for_trial(trial_name)

    evidence = getattr(page, "_esologs_observed_evidence", None)
    observed = evidence.slot(slot_name) if evidence is not None else None
    observed_gear = (
        tuple(name for name, _count in observed.observed_gear_sets)
        if observed is not None
        else ()
    )
    observed_skills = (
        tuple(name for name, _count in observed.observed_abilities)
        if observed is not None
        else ()
    )
    return page._comp_build_candidate_service.candidates_for_chair(
        goal=goal,
        slot_name=slot_name,
        role=role,
        preferred_class=preferred_class,
        observed_gear_sets=observed_gear,
        observed_skills=observed_skills,
    )


def _rename_goal_context_to_trial(page) -> None:
    host = page.goal_combo.parentWidget()
    if host is None:
        return
    for label in host.findChildren(QLabel):
        if label.text().strip().upper() == "GOAL":
            label.setText("TRIAL")
            break


def _refresh_sources_for_trial(page) -> None:
    if getattr(page, "_comp_trial_refresh_in_progress", False):
        return
    page._comp_trial_refresh_in_progress = True
    try:
        # Saved roster builds and versioned reference catalogs are local and are
        # re-queried by the candidate/picker refresh. ESO Logs is the live source.
        from ui import comp_builder_build_candidate_support as candidate_support
        from ui import comp_builder_candidate_picker_support as picker_support
        from ui import comp_builder_esologs_support as esologs_support

        candidate_support._refresh_candidates(page)
        picker_support._refresh_picker(page)
        esologs_support._refresh_live_esologs(page)
        candidate_support._refresh_candidates(page)
        picker_support._refresh_picker(page)
    finally:
        page._comp_trial_refresh_in_progress = False


def _schedule_trial_refresh(page) -> None:
    QTimer.singleShot(0, lambda: _refresh_sources_for_trial(page))


def _configure_trial_first_flow(page) -> None:
    selected = trial_for_selection(page.goal_combo.currentText())
    page.goal_combo.blockSignals(True)
    page.goal_combo.clear()
    page.goal_combo.addItems(COMP_MAKER_TRIALS)
    index = page.goal_combo.findText(selected)
    page.goal_combo.setCurrentIndex(index if index >= 0 else 0)
    page.goal_combo.blockSignals(False)
    _rename_goal_context_to_trial(page)

    # Rebuild the composition once using the selected trial after replacing the
    # legacy achievement selector, then make future trial changes refresh sources.
    page._load_for_goal()
    page.goal_combo.currentTextChanged.connect(lambda *_: _schedule_trial_refresh(page))

    send = getattr(page, "send_button", None)
    if send is not None:
        send.setText("Send Comp to Roster")
        send.setToolTip("Send these exact assigned builds and open recruitment chairs to Roster.")

    refresh = getattr(page, "refresh_esologs_button", None)
    if refresh is not None:
        refresh.setText("Refresh Build Sources")
        refresh.setToolTip(
            "Re-read roster/reference candidates and fetch current ranked-team evidence from ESO Logs."
        )
        # Replace the old ESO-Logs-only click with the complete source refresh.
        try:
            refresh.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        refresh.clicked.connect(lambda *_: _refresh_sources_for_trial(page))

    # Observed-class application is not part of the intended build-picking flow.
    apply_observed = getattr(page, "apply_esologs_button", None)
    if apply_observed is not None:
        apply_observed.hide()

    _schedule_trial_refresh(page)


def _comp_init_with_trial_flow(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _configure_trial_first_flow(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui import comp_builder_build_candidate_support as candidate_support
    from ui import comp_builder_esologs_support as esologs_support
    from ui.comp_builder_page import CompBuilderPage

    CompBuilderPage._matching_template = _matching_template_for_selected_trial
    candidate_support._chair_candidates = _chair_candidates_for_selected_trial
    esologs_support._current_trial = (
        lambda page: trial_for_selection(page.goal_combo.currentText())
    )

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_trial_flow
    _INSTALLED = True
