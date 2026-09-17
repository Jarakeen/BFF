from __future__ import annotations

"""Phase 14 pre-generation command center for Rotation Builder.

The existing Rotation V2 controls remain canonical. This layer moves those exact
widgets into the approved intent + obligations presentation and keeps result tabs
behind the generation boundary. It does not duplicate planner state.
"""

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


_INTENTS = {
    "Safe Progression": {
        "goal": "Progression / Difficult Content",
        "weaving": "Usually",
        "bar_swapping": "Prefer fewer swaps",
        "heavy_attacks": "Prefer safe windows",
        "complexity": "Simple",
        "reserve": 25,
        "survival": True,
        "description": "Consistent, forgiving, reliable performance.",
    },
    "Balanced": {
        "goal": "Sustainable",
        "weaving": "Usually",
        "bar_swapping": "Comfortable",
        "heavy_attacks": "Use when needed",
        "complexity": "Moderate",
        "reserve": 20,
        "survival": False,
        "description": "A balance of safety, sustain, and output.",
    },
    "Maximum Output": {
        "goal": "Damage",
        "weaving": "Reliable",
        "bar_swapping": "Comfortable",
        "heavy_attacks": "Avoid unless mandatory",
        "complexity": "High",
        "reserve": 10,
        "survival": False,
        "description": "Aggressive settings for experienced execution.",
    },
}


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def _field(title: str, widget: QWidget) -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    layout.addWidget(label)
    layout.addWidget(widget)
    return host


def _selected_build(page):
    try:
        return page._selected_build()
    except Exception:
        return None


def _skill_count(page) -> int:
    build = _selected_build(page)
    if build is None:
        return 0
    return sum(
        1
        for value in tuple(getattr(build, "FrontBarSkills", ()) or ())
        + tuple(getattr(build, "BackBarSkills", ()) or ())
        if str(value or "").strip()
    )


def _pressure_count(page) -> int:
    table = getattr(page, "rotation_pressure_table", None)
    return int(table.rowCount()) if table is not None else 0


def _set_combo_text(combo, text: str) -> None:
    index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)


def _apply_intent(page, name: str) -> None:
    values = _INTENTS[name]
    _set_combo_text(page.rotation_goal_combo, values["goal"])
    _set_combo_text(page.rotation_la_reliability_combo, values["weaving"])
    _set_combo_text(page.rotation_bar_swap_comfort_combo, values["bar_swapping"])
    _set_combo_text(page.rotation_heavy_behavior_combo, values["heavy_attacks"])
    _set_combo_text(page.rotation_complexity_combo, values["complexity"])
    page.rotation_minimum_reserve_spin.setValue(int(values["reserve"]))
    page.rotation_prioritize_survival.setChecked(bool(values["survival"]))
    page.phase14_rotation_intent = name
    for button_name, button in page.phase14_intent_buttons.items():
        button.blockSignals(True)
        button.setChecked(button_name == name)
        button.blockSignals(False)
    _refresh_setting_summary(page)


def _summary_row(title: str, value_label: QLabel) -> QWidget:
    row = QFrame()
    row.setProperty("rotationSummaryRow", True)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(8, 5, 8, 5)
    layout.addWidget(QLabel(title))
    layout.addStretch(1)
    layout.addWidget(value_label)
    return row


def _refresh_setting_summary(page) -> None:
    if not hasattr(page, "phase14_rotation_setting_labels"):
        return
    values = {
        "Weaving": page.rotation_la_reliability_combo.currentText(),
        "Bar swapping": page.rotation_bar_swap_comfort_combo.currentText(),
        "Heavy attacks": page.rotation_heavy_behavior_combo.currentText(),
        "Resource reserve": f"{page.rotation_minimum_reserve_spin.value()}%",
    }
    for key, label in page.phase14_rotation_setting_labels.items():
        label.setText(values[key])


def _obligation_row(page, title: str, description: str, count_text: str, detail: QWidget | None = None) -> QWidget:
    host = QWidget()
    outer = QVBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    button = QPushButton()
    button.setProperty("rotationObligationRow", True)
    row = QHBoxLayout(button)
    row.setContentsMargins(10, 7, 10, 7)
    row.addWidget(QLabel(title))
    description_label = QLabel(description)
    description_label.setProperty("muted", True)
    row.addWidget(description_label, 1)
    count = QLabel(count_text)
    count.setProperty("cardBadge", True)
    row.addWidget(count)
    row.addWidget(QLabel("›"))
    outer.addWidget(button)
    if detail is not None:
        detail.hide()
        outer.addWidget(detail)
        button.clicked.connect(lambda _checked=False, panel=detail: panel.setVisible(not panel.isVisible()))
    else:
        button.setEnabled(False)
    return host


def _build_advanced_panel(page) -> QWidget:
    panel = QFrame()
    panel.setProperty("foundryCard", True)
    grid = QGridLayout(panel)
    grid.setContentsMargins(10, 8, 10, 8)
    grid.setSpacing(8)
    grid.addWidget(_field("ROTATION GOAL", page.rotation_goal_combo), 0, 0)
    grid.addWidget(_field("WEAVING", page.rotation_la_reliability_combo), 0, 1)
    grid.addWidget(_field("BAR SWAPPING", page.rotation_bar_swap_comfort_combo), 1, 0)
    grid.addWidget(_field("HEAVY ATTACKS", page.rotation_heavy_behavior_combo), 1, 1)
    grid.addWidget(_field("COMPLEXITY", page.rotation_complexity_combo), 2, 0)
    grid.addWidget(_field("PRIMARY RESOURCE", page.rotation_primary_resource_combo), 2, 1)
    grid.addWidget(_field("MINIMUM RESERVE", page.rotation_minimum_reserve_spin), 3, 0)
    grid.addWidget(_field("ROTATION TYPE", page.rotation_type_combo), 3, 1)
    grid.addWidget(_field("EXECUTE STARTS", page.execute_spin), 4, 0)
    grid.addWidget(_field("TARGET TYPE", page.target_type_combo), 4, 1)
    grid.addWidget(page.rotation_prioritize_survival, 5, 0, 1, 2)
    grid.addWidget(page.rotation_human_reaction_time, 6, 0, 1, 2)
    grid.addWidget(page.rotation_prepare_for_pressure, 7, 0, 1, 2)
    return panel


def _build_setup_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    context = FoundryCard("Rotation Context", "✦")
    context_row = QHBoxLayout()
    context_row.setContentsMargins(0, 0, 0, 0)
    for title, control in (
        ("CHARACTER", page.character_combo),
        ("BUILD", page.build_combo),
        ("TEAM", page.rotation_team_combo),
        ("CONTENT", page.rotation_content_combo),
        ("BOSS", page.rotation_boss_combo),
        ("DIFFICULTY", page.rotation_threshold_difficulty_combo),
    ):
        control.show()
        context_row.addWidget(_field(title, control), 1)
    context.addLayout(context_row)
    layout.addWidget(context)

    columns = QHBoxLayout()
    columns.setSpacing(8)

    intent_card = FoundryCard("Rotation Intent", "◎")
    intent_card.addWidget(_muted("Choose a focus. FoundryDock applies a visible starting profile that you can adjust."))
    intent_buttons = QHBoxLayout()
    page.phase14_intent_buttons = {}
    for name, values in _INTENTS.items():
        button = QPushButton(f"{name}\n{values['description']}")
        button.setCheckable(True)
        button.setMinimumHeight(92)
        button.clicked.connect(lambda checked, intent=name: _apply_intent(page, intent) if checked else None)
        page.phase14_intent_buttons[name] = button
        intent_buttons.addWidget(button, 1)
    intent_card.addLayout(intent_buttons)

    intent_card.addWidget(QLabel("Generated Settings"))
    page.phase14_rotation_setting_labels = {
        name: QLabel() for name in ("Weaving", "Bar swapping", "Heavy attacks", "Resource reserve")
    }
    for name, value_label in page.phase14_rotation_setting_labels.items():
        intent_card.addWidget(_summary_row(name, value_label))

    page.phase14_rotation_advanced_panel = _build_advanced_panel(page)
    page.phase14_rotation_advanced_panel.hide()
    advanced_button = QPushButton("Advanced execution & sustain")
    advanced_button.clicked.connect(
        lambda: page.phase14_rotation_advanced_panel.setVisible(
            not page.phase14_rotation_advanced_panel.isVisible()
        )
    )
    intent_card.addWidget(advanced_button)
    intent_card.addWidget(page.phase14_rotation_advanced_panel)
    columns.addWidget(intent_card, 1)

    obligations = FoundryCard("Inputs & Obligations", "☑")
    obligations.addWidget(
        _muted("Detected from the selected build, encounter context, and canonical rules. Unknown evidence stays unknown.")
    )
    page.phase14_skill_count = QLabel()

    priority_host = QWidget()
    priority_layout = QVBoxLayout(priority_host)
    priority_layout.setContentsMargins(8, 4, 8, 8)
    page.priority_table.setMinimumHeight(210)
    priority_layout.addWidget(page.priority_table)

    pressure_host = QWidget()
    pressure_layout = QVBoxLayout(pressure_host)
    pressure_layout.setContentsMargins(8, 4, 8, 8)
    page.rotation_pressure_table.setMinimumHeight(160)
    pressure_layout.addWidget(page.rotation_pressure_table)

    obligations.addWidget(
        _obligation_row(page, "Build skills", "Skills and priorities from the selected saved build.", str(_skill_count(page)), priority_host)
    )
    obligations.addWidget(
        _obligation_row(page, "Gear procs", "Canonical proc obligations appear only when reviewed evidence is available.", "—")
    )
    obligations.addWidget(
        _obligation_row(page, "Team duties", "Assignments remain owned by roster/team context.", "—")
    )
    obligations.addWidget(
        _obligation_row(page, "Pressure windows", "Short intense encounter windows and custom reviewed windows.", str(_pressure_count(page)), pressure_host)
    )
    obligations.addWidget(
        _obligation_row(page, "Advanced rules", "Custom ability priorities and conditional logic.", "›", page.phase14_rotation_advanced_panel)
    )

    page.generate_button.setMinimumHeight(54)
    obligations.addWidget(page.generate_button)
    columns.addWidget(obligations, 1)

    layout.addLayout(columns, 1)
    return tab


def _enable_result_tabs(page, enabled: bool) -> None:
    tabs = page.rotation_builder_tabs
    for index in range(1, tabs.count()):
        tabs.setTabEnabled(index, enabled)


def _refresh_phase14_state(page) -> None:
    _refresh_setting_summary(page)
    if hasattr(page, "phase14_intent_buttons") and not getattr(page, "phase14_rotation_intent", ""):
        _apply_intent(page, "Safe Progression")
    has_result = bool(getattr(page, "rotation_plan", None))
    _enable_result_tabs(page, has_result)


def install_phase14_rotation_command_center(page) -> None:
    """Replace the V2 Builder tab with the approved Phase 14 command-center state."""
    if bool(getattr(page, "_phase14_rotation_command_center_installed", False)):
        return
    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is None or tabs.count() == 0:
        return

    old_builder = tabs.widget(0)
    setup = _build_setup_tab(page)
    tabs.removeTab(0)
    tabs.insertTab(0, setup, "Builder")
    tabs.setCurrentIndex(0)
    if old_builder is not None:
        old_builder.hide()
        old_builder.deleteLater()

    page.header.title.setText("Rotation Builder")
    page.header.subtitle.setText("Build smarter. Play longer. Survive the hard parts.")

    original_set_plan = page.set_rotation_plan
    original_clear_plan = page.clear_rotation_plan

    def set_plan_phase14(plan) -> None:
        original_set_plan(plan)
        _enable_result_tabs(page, bool(plan and tuple(getattr(plan, "actions", ()) or ())))

    def clear_plan_phase14(*, refresh: bool = True) -> None:
        original_clear_plan(refresh=refresh)
        _enable_result_tabs(page, False)
        tabs.setCurrentIndex(0)

    page.set_rotation_plan = set_plan_phase14
    page.clear_rotation_plan = clear_plan_phase14

    for control in (
        page.rotation_la_reliability_combo,
        page.rotation_bar_swap_comfort_combo,
        page.rotation_heavy_behavior_combo,
        page.rotation_minimum_reserve_spin,
    ):
        if hasattr(control, "currentTextChanged"):
            control.currentTextChanged.connect(lambda _value: _refresh_setting_summary(page))
        if hasattr(control, "valueChanged"):
            control.valueChanged.connect(lambda _value: _refresh_setting_summary(page))

    _refresh_phase14_state(page)
    page._phase14_rotation_command_center_installed = True


__all__ = ["install_phase14_rotation_command_center"]
