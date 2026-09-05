from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_SEND_TO_ROSTER = None


def _actions_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Actions":
            return card
    return None


def _effective_plan_name(page) -> str:
    explicit = page.plan_name_input.text().strip()
    if explicit:
        return explicit
    selection = page.goal_combo.currentText().strip() or "Raid"
    return f"{selection} Composition"


def _refresh_team_name(page) -> None:
    label = getattr(page, "comp_team_name_label", None)
    if label is not None:
        label.setText(f"TEAM / ROSTER PLAN: {_effective_plan_name(page)}")


def _send_completed(page, plan_name: str) -> None:
    name = str(plan_name or "").strip() or _effective_plan_name(page)
    page._comp_send_completed_name = name
    label = getattr(page, "comp_send_feedback_label", None)
    if label is not None:
        label.setText(f'Sent “{name}” to Roster ✓')
    page.status.success(f'Sent “{name}” to Roster.')


def _send_to_roster_with_feedback(self, *_args) -> None:
    assert _ORIGINAL_SEND_TO_ROSTER is not None

    name = _effective_plan_name(self)
    button = getattr(self, "send_button", None)
    feedback = getattr(self, "comp_send_feedback_label", None)
    self._comp_send_completed_name = ""

    if button is not None:
        button.setEnabled(False)
        button.setText("Sending Comp…")
    if feedback is not None:
        feedback.setText(f'Sending “{name}” to Roster…')
    self.status.info(f'Sending “{name}” to Roster…')
    QApplication.processEvents()

    try:
        _ORIGINAL_SEND_TO_ROSTER(self)
        if not self._comp_send_completed_name and feedback is not None:
            feedback.setText(f'Send did not complete for “{name}”. Check the status message above.')
    finally:
        if button is not None:
            button.setText("Send Comp to Roster")
            button.setEnabled(True)
        QApplication.processEvents()


def _install_feedback(page) -> None:
    actions = _actions_card(page)
    if actions is None:
        return

    page._comp_send_completed_name = ""
    page.comp_team_name_label = QLabel()
    page.comp_team_name_label.setWordWrap(True)
    page.comp_team_name_label.setProperty("compTeamName", True)

    page.comp_send_feedback_label = QLabel("Ready to send this comp when assignments are complete.")
    page.comp_send_feedback_label.setWordWrap(True)
    page.comp_send_feedback_label.setProperty("compSendFeedback", True)

    # Keep the identity/feedback near the actions without creating another card.
    actions.body_layout.insertWidget(0, page.comp_team_name_label)
    actions.body_layout.insertWidget(1, page.comp_send_feedback_label)

    page.plan_name_input.textChanged.connect(lambda *_: _refresh_team_name(page))
    page.goal_combo.currentTextChanged.connect(lambda *_: _refresh_team_name(page))
    page.rosterPlanSent.connect(lambda name: _send_completed(page, name))
    _refresh_team_name(page)


def _comp_init_with_send_feedback(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_feedback(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_SEND_TO_ROSTER
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_SEND_TO_ROSTER = CompBuilderPage._send_to_roster
    CompBuilderPage._send_to_roster = _send_to_roster_with_feedback

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_send_feedback
    _INSTALLED = True
