from __future__ import annotations

"""Shared compact context/action strip for Raid Plan workspace pages."""

from collections.abc import Iterable

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def _detach_header_host(page, widget: QWidget) -> None:
    host = widget.parentWidget()
    if host is None:
        return
    header = getattr(page, "header", None)
    context_layout = getattr(header, "context_layout", None)
    if context_layout is not None:
        context_layout.removeWidget(host)
    widget.setParent(None)
    host.hide()


def _field(title: str, widget: QWidget, *, minimum_width: int = 0) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    layout.addWidget(label)

    if minimum_width:
        widget.setMinimumWidth(minimum_width)
    layout.addWidget(widget)
    return host


def rehome_plan_header_controls(
    page,
    *,
    trailing_widgets: Iterable[QWidget] = (),
) -> QWidget:
    """Move planning inputs/actions out of FoundryHeader into one reusable strip."""

    existing = getattr(page, "plan_context_bar", None)
    if isinstance(existing, QWidget):
        for widget in trailing_widgets:
            actions = getattr(page, "plan_context_actions_layout", None)
            if actions is not None and widget.parentWidget() is not existing:
                widget.setParent(None)
                actions.addWidget(widget)
        return existing

    trial_combo = page.trial_combo
    difficulty_combo = page.difficulty_combo
    plan_name_edit = page.plan_name_edit
    saved_plan_combo = page.saved_plan_combo

    for widget in (trial_combo, difficulty_combo, plan_name_edit, saved_plan_combo):
        _detach_header_host(page, widget)

    buttons: list[QPushButton] = []
    for name in (
        "load_plan_button",
        "save_plan_button",
        "publish_plan_finch_button",
        "get_shared_plans_button",
        "delete_plan_button",
    ):
        button = getattr(page, name, None)
        if isinstance(button, QPushButton):
            button.setParent(None)
            buttons.append(button)

    shared = getattr(page, "get_shared_plans_button", None)
    if isinstance(shared, QPushButton):
        shared.setText("Shared Plans")
        shared.setMinimumWidth(92)

    bar = QWidget()
    bar.setProperty("raidPlanContextBar", True)
    row = QHBoxLayout(bar)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    row.addWidget(_field("TRIAL", trial_combo, minimum_width=180), 3)
    row.addWidget(_field("DIFFICULTY", difficulty_combo, minimum_width=150), 2)
    row.addWidget(_field("PLAN", plan_name_edit, minimum_width=210), 3)
    row.addWidget(_field("SAVED PLAN", saved_plan_combo, minimum_width=220), 3)

    actions_host = QWidget()
    actions_layout = QVBoxLayout(actions_host)
    actions_layout.setContentsMargins(0, 0, 0, 0)
    actions_layout.setSpacing(2)
    actions_label = QLabel("PLAN ACTIONS")
    actions_label.setProperty("sidebarHeading", True)
    actions_layout.addWidget(actions_label)

    action_row = QHBoxLayout()
    action_row.setContentsMargins(0, 0, 0, 0)
    action_row.setSpacing(6)
    for button in buttons:
        action_row.addWidget(button)
    for widget in trailing_widgets:
        widget.setParent(None)
        action_row.addWidget(widget)
    actions_layout.addLayout(action_row)

    row.addWidget(actions_host, 0)

    page.plan_context_bar = bar
    page.plan_context_actions_layout = action_row
    return bar


__all__ = ["rehome_plan_header_controls"]
