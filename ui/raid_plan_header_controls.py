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
    plan_identity_widget: QWidget | None = None,
    team_identity_widget: QWidget | None = None,
    show_plan_editor: bool = True,
    show_team_editor: bool = True,
    show_saved_plan_selector: bool = True,
) -> QWidget:
    """Move planning context/actions out of FoundryHeader into one reusable strip.

    The City Raid Plan workspace can keep persisted identity read-only while still
    reusing the legacy editor widgets internally for New Plan creation and state.
    """

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
    team_combo = getattr(page, "team_combo", None)

    detachable = [trial_combo, difficulty_combo, plan_name_edit, saved_plan_combo]
    if isinstance(team_combo, QWidget):
        detachable.append(team_combo)
    for widget in detachable:
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

    if plan_identity_widget is not None:
        row.addWidget(_field("PLAN", plan_identity_widget, minimum_width=180), 2)
    elif show_plan_editor:
        row.addWidget(_field("PLAN", plan_name_edit, minimum_width=210), 3)
    else:
        plan_name_edit.hide()
        plan_name_edit.setParent(bar)

    if team_identity_widget is not None:
        row.addWidget(_field("TEAM", team_identity_widget, minimum_width=160), 2)
    elif isinstance(team_combo, QWidget) and show_team_editor:
        row.addWidget(_field("TEAM", team_combo, minimum_width=180), 2)
    elif isinstance(team_combo, QWidget):
        team_combo.hide()
        team_combo.setParent(bar)

    if show_saved_plan_selector:
        row.addWidget(_field("SAVED PLAN", saved_plan_combo, minimum_width=220), 3)
    else:
        saved_plan_combo.hide()
        saved_plan_combo.setParent(bar)

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
