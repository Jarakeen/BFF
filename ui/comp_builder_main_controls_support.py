from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _actions_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Actions":
            return card
    return None


def _detach_widget(widget: QWidget | None) -> QWidget | None:
    if widget is None:
        return None
    parent = widget.parentWidget()
    layout = parent.layout() if parent is not None else None
    if layout is not None:
        layout.removeWidget(widget)
    return widget


def _row(*widgets: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    for widget in widgets:
        row.addWidget(widget, 1)
    return row


def _install_main_controls(page) -> None:
    actions = _actions_card(page)
    if actions is None:
        return

    # The right-side Actions card is the single control surface for Comp Maker.
    # Re-home working buttons rather than duplicating callbacks or state.
    generate = _detach_widget(getattr(page, "apply_all_comp_candidates_button", None))
    apply_chair = _detach_widget(getattr(page, "apply_comp_candidate_button", None))
    recommended = _detach_widget(getattr(page, "recommended_button", None))
    reset = _detach_widget(getattr(page, "reset_button", None))
    refresh_logs = _detach_widget(getattr(page, "refresh_esologs_button", None))
    apply_logs = _detach_widget(getattr(page, "apply_esologs_button", None))

    if generate is not None:
        generate.setText("Generate Team")
        generate.setProperty("compPrimaryGenerate", True)
    if apply_chair is not None:
        # The selected matrix row is the destination. Candidate ranking on the
        # right supplies the source build, so use assignment language rather than
        # the old implementation-centric "apply candidate" wording.
        apply_chair.setText("Assign Build to This Player")
        apply_chair.setProperty("compAssignBuild", True)

    # Keep the existing plan-name, style, roster/save/load and strategy controls in
    # the card. Insert the ordinary Comp Maker workflow immediately after the style
    # help so the primary path is visible before optional strategy discovery.
    insert_at = min(3, actions.body_layout.count())

    primary = tuple(widget for widget in (generate, apply_chair) if widget is not None)
    if primary:
        actions.body_layout.insertLayout(insert_at, _row(*primary))
        insert_at += 1

    template = tuple(widget for widget in (recommended, reset) if widget is not None)
    if template:
        actions.body_layout.insertLayout(insert_at, _row(*template))
        insert_at += 1

    logs = tuple(widget for widget in (refresh_logs, apply_logs) if widget is not None)
    if logs:
        actions.body_layout.insertLayout(insert_at, _row(*logs))

    # Old header hosts become empty after their buttons move; hide them so the comp
    # card remains focused on the 12-chair overview.
    header_action_host = getattr(page.matrix_card, "header_action_layout", None)
    if header_action_host is not None:
        for index in range(header_action_host.count()):
            item = header_action_host.itemAt(index)
            widget = item.widget()
            if widget is not None and not widget.findChildren(QWidget):
                widget.hide()


def _comp_init_with_main_controls(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_main_controls(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_main_controls
    _INSTALLED = True
