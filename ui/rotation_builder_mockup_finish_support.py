from __future__ import annotations

"""Polish the Rotation Builder V2 workspace to the approved six-tab mockup.

This presentation layer only reorganizes live canonical widgets and already-existing
results. It deliberately does not invent proc, encounter, sustain, or team evidence.
Controls that are not yet planner inputs are labeled as workspace-only until their
canonical service contracts are promoted.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _tab(page, title: str) -> QWidget | None:
    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is None:
        return None
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return tabs.widget(index)
    return None


def _clear(layout, *, preserve=()) -> None:
    keep = set(preserve)
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _clear(nested, preserve=keep)
        widget = item.widget()
        if widget is not None and widget not in keep:
            widget.setParent(None)
            widget.deleteLater()


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


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def _remove_header_wrapper(page, control) -> None:
    wrapper = control.parentWidget()
    layout = getattr(page.header, "context_layout", None)
    if wrapper is None or layout is None:
        return
    for index in range(layout.count() - 1, -1, -1):
        item = layout.itemAt(index)
        if item is not None and item.widget() is wrapper:
            layout.takeAt(index)
            wrapper.setParent(None)
            wrapper.deleteLater()
            return


def _rebuild_context(page) -> None:
    card = _card(page, "Build & Context")
    if card is None:
        return

    controls = (
        page.character_combo,
        page.build_combo,
        page.rotation_content_combo,
        page.rotation_boss_combo,
        page.rotation_goal_combo,
        page.build_summary,
        page.food_value,
    )
    for control in controls[:4]:
        _remove_header_wrapper(page, control)

    _clear(card.body_layout, preserve=controls)
    row = QGridLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setHorizontalSpacing(8)
    for column in range(5):
        row.setColumnStretch(column, 1)
    row.addWidget(_field("CHARACTER", page.character_combo), 0, 0)
    row.addWidget(_field("BUILD", page.build_combo), 0, 1)
    row.addWidget(_field("CONTENT", page.rotation_content_combo), 0, 2)
    row.addWidget(_field("BOSS (OPTIONAL)", page.rotation_boss_combo), 0, 3)
    row.addWidget(_field("ROTATION GOAL", page.rotation_goal_combo), 0, 4)
    card.addLayout(row)

    detail = QHBoxLayout()
    detail.addWidget(page.build_summary, 3)
    food = page._labelled_value("SAVED FOOD", page.food_value)
    detail.addWidget(food, 1)
    card.addLayout(detail)


def _style_choice(title: str, description: str) -> tuple[QWidget, QRadioButton]:
    host = QWidget()
    host.setProperty("rotationStyleChoice", True)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(4)
    radio = QRadioButton(title)
    radio.setProperty("rotationStyleRadio", True)
    label = _muted(description)
    layout.addWidget(radio)
    layout.addWidget(label)
    return host, radio


def _rebuild_style(page) -> None:
    card = _card(page, "Rotation Style")
    if card is None:
        return
    _clear(card.body_layout, preserve=(page.rotation_type_combo, page.execute_spin, page.target_type_combo))
    page.rotation_type_combo.hide()

    choices = QHBoxLayout()
    page.rotation_style_group = QButtonGroup(page)
    specs = (
        ("Static", "Fixed sequence. Best for simple, predictable rotations."),
        ("Semi-static", "Core loop with intelligent refreshes and timing adjustments."),
        ("Dynamic", "Priority-based. Adapts to changing fight conditions."),
    )
    for title, description in specs:
        host, radio = _style_choice(title, description)
        page.rotation_style_group.addButton(radio)
        choices.addWidget(host, 1)
        radio.toggled.connect(
            lambda checked, value=title: page.rotation_type_combo.setCurrentText(value)
            if checked
            else None
        )
        if page.rotation_type_combo.currentText() == title:
            radio.setChecked(True)
    card.addLayout(choices)

    lower = QHBoxLayout()
    lower.addWidget(_field("EXECUTE STARTS", page.execute_spin), 1)
    lower.addWidget(_field("TARGET TYPE", page.target_type_combo), 1)
    card.addLayout(lower)


def _rebuild_rules(page) -> None:
    card = _card(page, "Rotation Rules & Requirements")
    if card is None:
        return
    _clear(card.body_layout, preserve=(page.priority_table,))

    tabs = QTabWidget()
    tabs.setDocumentMode(True)
    page.rotation_rule_tabs = tabs

    detected = QWidget()
    detected_layout = QVBoxLayout(detected)
    detected_layout.setContentsMargins(0, 0, 0, 0)
    detected_layout.addWidget(
        _muted("Live saved-bar priorities. Gear and set obligations join this surface only when reviewed canonical evidence exists.")
    )
    page.priority_table.setMinimumHeight(250)
    detected_layout.addWidget(page.priority_table)
    tabs.addTab(detected, "Detected from Build")

    team = QWidget()
    team_layout = QVBoxLayout(team)
    team_layout.setContentsMargins(0, 0, 0, 0)
    page.rotation_team_rules_label = _muted(
        "No team rotation obligations are currently attached. Team-aware duties will appear here from explicit Raid Plan / Assignment evidence."
    )
    team_layout.addWidget(page.rotation_team_rules_label)
    team_layout.addStretch()
    tabs.addTab(team, "Team Assignments")

    encounter = QWidget()
    encounter_layout = QVBoxLayout(encounter)
    encounter_layout.setContentsMargins(0, 0, 0, 0)
    page.rotation_encounter_rules_label = _muted(
        "Reviewed encounter obligations and pressure windows appear here when the selected encounter has canonical evidence."
    )
    encounter_layout.addWidget(page.rotation_encounter_rules_label)
    encounter_layout.addStretch()
    tabs.addTab(encounter, "Encounter Windows")

    custom = QWidget()
    custom_layout = QVBoxLayout(custom)
    custom_layout.setContentsMargins(0, 0, 0, 0)
    page.rotation_custom_rule_table = QTableWidget(0, 4)
    page.rotation_custom_rule_table.setHorizontalHeaderLabels(
        ["Requirement", "Cadence / Window", "Priority", "Reason"]
    )
    page.rotation_custom_rule_table.verticalHeader().setVisible(False)
    page.rotation_custom_rule_table.horizontalHeader().setStretchLastSection(True)
    page.rotation_custom_rule_table.setMinimumHeight(210)
    custom_layout.addWidget(page.rotation_custom_rule_table)
    buttons = QHBoxLayout()
    add = QPushButton("Add Custom Rule")
    remove = QPushButton("Remove")

    def add_rule() -> None:
        row = page.rotation_custom_rule_table.rowCount()
        page.rotation_custom_rule_table.insertRow(row)
        for column, value in enumerate(("Custom requirement", "", "High", "")):
            page.rotation_custom_rule_table.setItem(row, column, QTableWidgetItem(value))

    def remove_rule() -> None:
        row = page.rotation_custom_rule_table.currentRow()
        if row >= 0:
            page.rotation_custom_rule_table.removeRow(row)

    add.clicked.connect(add_rule)
    remove.clicked.connect(remove_rule)
    buttons.addWidget(add)
    buttons.addWidget(remove)
    buttons.addStretch()
    custom_layout.addLayout(buttons)
    custom_layout.addWidget(_muted("Custom rules are saved only in this workspace for now; they are not silently promoted into planner truth."))
    tabs.addTab(custom, "Custom Rules")

    card.addWidget(tabs)


def _rebuild_pressure(page) -> None:
    card = _card(page, "Pressure Windows")
    if card is None:
        return
    table = page.rotation_pressure_table
    table.setColumnCount(6)
    table.setHorizontalHeaderLabels(
        ["Event", "Start / Trigger", "Duration", "Impact", "Reserve", "Recovery"]
    )
    table.setMinimumHeight(205)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.horizontalHeader().setStretchLastSection(True)

    try:
        page.rotation_add_pressure_button.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass
    try:
        page.rotation_remove_pressure_button.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass

    def add_window() -> None:
        row = table.rowCount()
        table.insertRow(row)
        values = ("Custom pressure window", "", "6s", "Extreme", "75%", "No")
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))

    def remove_window() -> None:
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    page.rotation_add_pressure_button.clicked.connect(add_window)
    page.rotation_remove_pressure_button.clicked.connect(remove_window)


def _rebuild_timeline(page) -> None:
    tab = _tab(page, "Timeline")
    if tab is None:
        return
    layout = tab.layout()
    if layout is None:
        return
    _clear(layout, preserve=(page.rotation_timeline_widget, page.timeline_table, page.timeline_hint))

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(8)
    grid.setColumnStretch(0, 4)
    grid.setColumnStretch(1, 1)

    visual = FoundryCard("Rotation Timeline", "◇").set_watermark("compass", 0.035)
    page.rotation_timeline_widget.setMinimumHeight(300)
    visual.addWidget(page.rotation_timeline_widget)
    grid.addWidget(visual, 0, 0, 1, 2)

    actions = FoundryCard("Rotation Actions (in order)", "☷").set_watermark("compass", 0.03)
    page.timeline_table.setVisible(True)
    page.timeline_table.setMinimumHeight(270)
    actions.addWidget(page.timeline_table)
    actions.addWidget(page.timeline_hint)
    grid.addWidget(actions, 1, 0)

    options = FoundryCard("Timeline Options", "◆").set_watermark("compass", 0.03)
    show_visual = QCheckBox("Show visual timeline")
    show_actions = QCheckBox("Show action table")
    show_visual.setChecked(True)
    show_actions.setChecked(True)
    show_visual.toggled.connect(page.rotation_timeline_widget.setVisible)
    show_actions.toggled.connect(page.timeline_table.setVisible)
    reset = QPushButton("Reset View")
    reset.clicked.connect(lambda: (show_visual.setChecked(True), show_actions.setChecked(True)))
    options.addWidget(show_visual)
    options.addWidget(show_actions)
    options.addWidget(_muted("Skill icons are resolved from the existing AbilityIcons asset library. Timeline rendering remains visual evidence, not rotation authority."))
    options.addWidget(reset)
    grid.addWidget(options, 1, 1)
    layout.addLayout(grid)


def _rebuild_resources(page) -> None:
    tab = _tab(page, "Uptime & Resources")
    if tab is None:
        return
    layout = tab.layout()
    if layout is None:
        return
    cadence = getattr(page, "cadence_progression_card", None)
    preserve = [page.sustain_graph, page.resource_summary, page.resource_detail, page.duration_evidence_card]
    if cadence is not None:
        preserve.append(cadence)
    _clear(layout, preserve=tuple(preserve))

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(8)
    grid.setColumnStretch(0, 2)
    grid.setColumnStretch(1, 1)

    uptime = FoundryCard("Buff & Debuff Uptime", "◇").set_watermark("compass", 0.035)
    uptime.addWidget(page.duration_evidence_card)
    grid.addWidget(uptime, 0, 0)

    proc = FoundryCard("Set Proc Monitoring", "◆").set_watermark("compass", 0.035)
    page.rotation_proc_status_label = _muted(
        "Reviewed proc cadence evidence will appear here. Unreviewed gear prose is not converted into fake proc timing."
    )
    proc.addWidget(page.rotation_proc_status_label)
    if cadence is not None:
        proc.addWidget(cadence)
    grid.addWidget(proc, 0, 1)

    resources = FoundryCard("Resource Graphs", "◈").set_watermark("compass", 0.04)
    resources.addWidget(page.sustain_graph)
    resources.addWidget(page.resource_summary)
    resources.addWidget(page.resource_detail)
    grid.addWidget(resources, 1, 0, 1, 2)
    layout.addLayout(grid)


def _refresh_explanation_sidebars(page) -> None:
    plan = getattr(page, "rotation_plan", None)
    if not hasattr(page, "rotation_optimization_notes_label"):
        return
    if plan is None:
        page.rotation_optimization_notes_label.setText("Generate a rotation to evaluate the current plan.")
        page.rotation_warning_notes_label.setText("No generated plan yet.")
        return

    unresolved = tuple(getattr(plan, "unresolved", ()) or ())
    checks = [
        "✓ Rotation plan generated",
        f"✓ {len(tuple(getattr(plan, 'actions', ()) or ()))} scheduled actions",
    ]
    resource_text = str(getattr(page, "resource_summary", QLabel()).text() or "")
    if "SUSTAINS" in resource_text:
        checks.append("✓ Modeled resource timeline sustains")
    elif "FAILS" in resource_text:
        checks.append("! Modeled resource timeline does not sustain")
    page.rotation_optimization_notes_label.setText("\n".join(checks))

    if unresolved:
        page.rotation_warning_notes_label.setText("\n".join(f"• {item}" for item in unresolved))
    else:
        page.rotation_warning_notes_label.setText("No schedule-level unresolved items reported.")


def _rebuild_explanations(page) -> None:
    tab = _tab(page, "Explanations")
    if tab is None:
        return
    layout = tab.layout()
    if layout is None:
        return
    _clear(layout, preserve=(page.rotation_explanation_label, page.notes_edit))

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(8)
    grid.setColumnStretch(0, 2)
    grid.setColumnStretch(1, 1)

    explanation = FoundryCard("Rotation Explanation", "◇").set_watermark("compass", 0.035)
    explanation.addWidget(page.rotation_explanation_label)
    grid.addWidget(explanation, 0, 0, 2, 1)

    optimization = FoundryCard("Optimization Notes", "◆").set_watermark("compass", 0.03)
    page.rotation_optimization_notes_label = QLabel()
    page.rotation_optimization_notes_label.setWordWrap(True)
    optimization.addWidget(page.rotation_optimization_notes_label)
    grid.addWidget(optimization, 0, 1)

    warnings = FoundryCard("Warnings / Considerations", "⚑").set_watermark("compass", 0.03)
    page.rotation_warning_notes_label = QLabel()
    page.rotation_warning_notes_label.setWordWrap(True)
    warnings.addWidget(page.rotation_warning_notes_label)
    grid.addWidget(warnings, 1, 1)

    notes = FoundryCard("Personal Notes", "✎").set_watermark("feather", 0.04)
    page.notes_edit.setMaximumHeight(150)
    notes.addWidget(page.notes_edit)
    grid.addWidget(notes, 2, 0, 1, 2)
    layout.addLayout(grid)
    _refresh_explanation_sidebars(page)


def _polish_tabs(page) -> None:
    tabs = page.rotation_builder_tabs
    tabs.setUsesScrollButtons(False)
    tabs.setElideMode(Qt.TextElideMode.ElideNone)
    tabs.tabBar().setExpanding(False)
    tabs.setToolTip("Rotation Builder workspace: define, inspect, compare, explain, save, and export one rotation.")


def _install_result_refresh(page) -> None:
    original_set_plan = page.set_rotation_plan
    original_clear = page.clear_rotation_plan

    def set_plan_mockup(plan) -> None:
        original_set_plan(plan)
        _refresh_explanation_sidebars(page)

    def clear_plan_mockup(*, refresh: bool = True) -> None:
        original_clear(refresh=refresh)
        _refresh_explanation_sidebars(page)

    page.set_rotation_plan = set_plan_mockup
    page.clear_rotation_plan = clear_plan_mockup


def install_rotation_builder_mockup_finish(page) -> None:
    """Apply the approved visual composition over the functional V2 tab workspace."""
    if bool(getattr(page, "_rotation_builder_mockup_finish_installed", False)):
        return
    if not hasattr(page, "rotation_builder_tabs"):
        raise RuntimeError("Rotation Builder V2 tabs must be installed before mockup finish")

    page.header.title.setText("Rotation Builder")
    page.header.subtitle.setText("Build smarter. Play longer. Survive the hard parts.")
    page.header.department.setText("RAID ENGINE • ROTATIONS")

    _polish_tabs(page)
    _rebuild_context(page)
    _rebuild_style(page)
    _rebuild_rules(page)
    _rebuild_pressure(page)
    _rebuild_timeline(page)
    _rebuild_resources(page)
    _rebuild_explanations(page)
    _install_result_refresh(page)
    page._rotation_builder_mockup_finish_installed = True


__all__ = ["install_rotation_builder_mockup_finish"]
