from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

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


def _hide_update_context(page) -> None:
    # Comp Maker assumes the current live game update for now. Hide the disabled
    # header field rather than carrying a redundant Update 50/51 box in the UI.
    update_combo = getattr(page, "update_combo", None)
    if update_combo is None:
        return
    host = update_combo.parentWidget()
    if host is not None:
        host.hide()
    else:
        update_combo.hide()


def _hide_strategy_action(page) -> None:
    # Keep the underlying experimental machinery available for later, but remove
    # its dedicated button from the normal Comp Maker workflow for now.
    button = getattr(page, "comp_interesting_strategy_button", None)
    if button is not None:
        button.hide()
    for label in page.findChildren(QLabel):
        if label.property("compInterestingStrategyHelp"):
            label.hide()


def _move_plan_controls_to_header(page) -> None:
    """Put plan identity/style beside Trial and Difficulty to reclaim build space."""
    plan_name = getattr(page, "plan_name_input", None)
    style_combo = getattr(page, "comp_composition_style_combo", None)

    for label in page.findChildren(QLabel):
        text = label.text().strip().upper()
        if text in {"PLAN NAME", "COMPOSITION STYLE"}:
            label.hide()
        if label.property("compCompositionStyleHelp"):
            label.hide()

    if plan_name is not None:
        plan_name.setMinimumWidth(210)
        page.header.add_context_widget(page._context_field("PLAN NAME", plan_name))

    if style_combo is not None:
        style_combo.setMinimumWidth(180)
        help_label = getattr(page, "comp_composition_style_help", None)
        if help_label is not None and help_label.text().strip():
            style_combo.setToolTip(help_label.text().strip())
        page.header.add_context_widget(page._context_field("PLAN STYLE", style_combo))


def _install_main_controls(page) -> None:
    actions = _actions_card(page)
    if actions is None:
        return

    _hide_update_context(page)
    _hide_strategy_action(page)
    _move_plan_controls_to_header(page)

    # The right-side Actions card is the compact execution surface. Re-home the
    # working buttons rather than duplicating callbacks or state.
    generate = _detach_widget(getattr(page, "apply_all_comp_candidates_button", None))
    apply_chair = _detach_widget(getattr(page, "apply_comp_candidate_button", None))
    recommended = _detach_widget(getattr(page, "recommended_button", None))
    reset = _detach_widget(getattr(page, "reset_button", None))
    refresh_logs = _detach_widget(getattr(page, "refresh_esologs_button", None))
    apply_logs = _detach_widget(getattr(page, "apply_esologs_button", None))

    if generate is not None:
        generate.setText("↵ Fill from Roster")
        generate.setProperty("compPrimaryGenerate", True)
        generate.setToolTip(
            "Fill every currently open raid chair with the best eligible saved roster build "
            "while preserving existing assignments and required provider coverage."
        )
    if apply_chair is not None:
        apply_chair.setText("↰ Assign Build to Player")
        apply_chair.setProperty("compAssignBuild", True)
        apply_chair.setToolTip(
            "Assign the selected candidate build to the highlighted player/chair."
        )

    # With plan identity and style moved to the header, the remaining controls can
    # begin at the top of the card instead of leaving dead form rows above them.
    insert_at = 0

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

    actions.set_body_margins(8, 5, 8, 6)
    actions.set_body_spacing(4)

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
    from ui.raid_engine_dashboard_support import install as install_raid_engine_dashboard

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_main_controls
    install_raid_engine_dashboard()
    _INSTALLED = True
