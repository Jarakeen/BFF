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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard
from ui.ux_icons import icon, icon_label, set_button_icon


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
        "icon": "shield",
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
        "icon": "scales",
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
        "icon": "optimization",
    },
}

_SETTING_ICONS = {
    "Weaving": "cog",
    "Bar swapping": "swapping",
    "Heavy attacks": "sword",
    "Resource reserve": "drop",
}

_OBLIGATION_ICONS = {
    "Build skills": "book-open-text",
    "Gear procs": "cog",
    "Team duties": "roster",
    "Pressure windows": "warning",
    "Advanced rules": "uptime",
}

_CONTEXT_FIELDS = (
    ("CHARACTER", "user", "character_combo"),
    ("BUILD", "builds", "build_combo"),
    ("TEAM", "roster", "rotation_team_combo"),
    ("TRIAL", "trial", "rotation_content_combo"),
    ("BOSS", "boss", "rotation_boss_combo"),
    ("DIFFICULTY", "crossed-swords", "rotation_threshold_difficulty_combo"),
)

_RESULT_TABS = (
    (1, "Timeline", "hourglass"),
    (2, "Uptime & Resources", "filter"),
    (3, "Explanations", "binoculars"),
    (4, "Compare", "scales"),
    (5, "Save & Export", "download"),
)


def _muted(text: str, *, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(wrap)
    label.setProperty("muted", True)
    return label


def _field(title: str, widget: QWidget, *, icon_name: str = "") -> QWidget:
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)

    heading = QHBoxLayout()
    heading.setContentsMargins(0, 0, 0, 0)
    heading.setSpacing(5)
    if icon_name:
        heading.addWidget(icon_label(icon_name, 14))
    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    label.setMaximumHeight(17)
    heading.addWidget(label)
    heading.addStretch(1)
    layout.addLayout(heading)

    widget.setMinimumHeight(32)
    widget.setMaximumHeight(32)
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
    page.phase14_applying_intent = True
    try:
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
    finally:
        page.phase14_applying_intent = False
    _refresh_setting_summary(page)


def _summary_row(title: str, value_label: QLabel) -> QWidget:
    row = QFrame()
    row.setProperty("rotationSummaryRow", True)
    row.setMinimumHeight(48)
    row.setMaximumHeight(54)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(12, 5, 12, 5)
    layout.setSpacing(9)
    layout.addWidget(icon_label(_SETTING_ICONS[title], 22))
    title_label = QLabel(title)
    title_label.setProperty("rotationSettingTitle", True)
    layout.addWidget(title_label)
    layout.addStretch(1)
    layout.addWidget(value_label)
    return row


def _is_customized(page) -> bool:
    name = str(getattr(page, "phase14_rotation_intent", "") or "")
    values = _INTENTS.get(name)
    if not values:
        return False
    return any(
        (
            page.rotation_goal_combo.currentText() != values["goal"],
            page.rotation_la_reliability_combo.currentText() != values["weaving"],
            page.rotation_bar_swap_comfort_combo.currentText() != values["bar_swapping"],
            page.rotation_heavy_behavior_combo.currentText() != values["heavy_attacks"],
            page.rotation_complexity_combo.currentText() != values["complexity"],
            page.rotation_minimum_reserve_spin.value() != int(values["reserve"]),
            page.rotation_prioritize_survival.isChecked() != bool(values["survival"]),
        )
    )


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
    customized = _is_customized(page)
    page.phase14_rotation_customized_label.setText("Customized" if customized else "Preset defaults")
    page.phase14_rotation_reset_button.setVisible(customized)


def _refresh_obligation_counts(page) -> None:
    labels = getattr(page, "phase14_obligation_count_labels", {})
    if "Build skills" in labels:
        labels["Build skills"].setText(str(_skill_count(page)))
    if "Pressure windows" in labels:
        labels["Pressure windows"].setText(str(_pressure_count(page)))


def _context_value(combo, fallback: str) -> str:
    text = str(combo.currentText() or "").strip()
    return text or fallback


def _refresh_context_summary(page) -> None:
    summary_label = getattr(page, "phase14_context_summary_label", None)
    values = {
        "CHARACTER": _context_value(page.character_combo, "No character"),
        "BUILD": _context_value(page.build_combo, "No build"),
        "TEAM": _context_value(page.rotation_team_combo, "No team context"),
        "TRIAL": _context_value(page.rotation_content_combo, "All Content"),
        "BOSS": _context_value(page.rotation_boss_combo, "No boss"),
        "DIFFICULTY": _context_value(page.rotation_threshold_difficulty_combo, "Select difficulty"),
    }
    for key, label in getattr(page, "phase14_context_value_labels", {}).items():
        label.setText(values[key])
    if summary_label is not None:
        summary_label.setText(
            f"{values['CHARACTER']} · {values['BUILD']} | "
            f"{values['TRIAL']} · {values['BOSS']} · {values['DIFFICULTY']} | {values['TEAM']}"
        )


def _toggle_context_controls(page) -> None:
    panel = page.phase14_context_controls_panel
    visible = not panel.isVisible()
    panel.setVisible(visible)
    page.phase14_context_edit_button.setText("Done" if visible else "Edit Context")


def _context_chip(title: str, icon_name: str, value_label: QLabel) -> QWidget:
    host = QFrame()
    host.setProperty("rotationContextChip", True)
    layout = QHBoxLayout(host)
    layout.setContentsMargins(8, 5, 8, 5)
    layout.setSpacing(6)
    layout.addWidget(icon_label(icon_name, 20))
    value_label.setProperty("rotationContextValue", True)
    value_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    value_label.setToolTip(title.title())
    layout.addWidget(value_label)
    return host


def _obligation_row(
    page,
    title: str,
    description: str,
    count_text: str,
    detail: QWidget | None = None,
) -> QWidget:
    host = QWidget()
    outer = QVBoxLayout(host)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    button = QPushButton()
    button.setProperty("rotationObligationRow", True)
    button.setMinimumHeight(54)
    button.setMaximumHeight(58)
    row = QHBoxLayout(button)
    row.setContentsMargins(11, 6, 10, 6)
    row.setSpacing(8)

    row.addWidget(icon_label(_OBLIGATION_ICONS[title], 23))
    title_label = QLabel(title)
    title_label.setMinimumWidth(112)
    title_label.setProperty("rotationObligationTitle", True)
    row.addWidget(title_label)

    description_label = _muted(description, wrap=False)
    description_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    row.addWidget(description_label, 1)

    count = QLabel(count_text)
    count.setProperty("cardBadge", True)
    count.setMinimumWidth(34)
    page.phase14_obligation_count_labels[title] = count
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
    grid.setSpacing(7)
    grid.addWidget(_field("ROTATION GOAL", page.rotation_goal_combo, icon_name="optimization"), 0, 0)
    grid.addWidget(_field("WEAVING", page.rotation_la_reliability_combo, icon_name="cog"), 0, 1)
    grid.addWidget(_field("BAR SWAPPING", page.rotation_bar_swap_comfort_combo, icon_name="swapping"), 1, 0)
    grid.addWidget(_field("HEAVY ATTACKS", page.rotation_heavy_behavior_combo, icon_name="sword"), 1, 1)
    grid.addWidget(_field("COMPLEXITY", page.rotation_complexity_combo, icon_name="uptime"), 2, 0)
    grid.addWidget(_field("PRIMARY RESOURCE", page.rotation_primary_resource_combo, icon_name="drop"), 2, 1)
    grid.addWidget(_field("MINIMUM RESERVE", page.rotation_minimum_reserve_spin, icon_name="drop"), 3, 0)
    grid.addWidget(_field("ROTATION TYPE", page.rotation_type_combo, icon_name="rotations"), 3, 1)
    grid.addWidget(_field("EXECUTE STARTS", page.execute_spin, icon_name="sword"), 4, 0)
    grid.addWidget(_field("TARGET TYPE", page.target_type_combo, icon_name="boss"), 4, 1)
    grid.addWidget(page.rotation_prioritize_survival, 5, 0, 1, 2)
    grid.addWidget(page.rotation_human_reaction_time, 6, 0, 1, 2)
    grid.addWidget(page.rotation_prepare_for_pressure, 7, 0, 1, 2)
    return panel


def _build_rules_detail() -> QWidget:
    detail = QFrame()
    detail.setProperty("foundryCard", True)
    layout = QVBoxLayout(detail)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.addWidget(
        _muted(
            "Ability-priority editing is available under Build skills. Additional conditional rule editors stay hidden until their canonical planner contracts are implemented."
        )
    )
    return detail


def _build_context(page) -> FoundryCard:
    context = FoundryCard("Rotation Context", "rotations")
    context.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    summary_row = QHBoxLayout()
    summary_row.setContentsMargins(0, 1, 0, 1)
    summary_row.setSpacing(6)

    # Compatibility/accessibility summary retained off-layout while the visible
    # state uses icon-led context chips.
    page.phase14_context_summary_label = QLabel()
    page.phase14_context_value_labels = {}
    for title, icon_name, _attribute in _CONTEXT_FIELDS:
        value = QLabel()
        page.phase14_context_value_labels[title] = value
        summary_row.addWidget(_context_chip(title, icon_name, value))
    summary_row.addStretch(1)

    page.phase14_context_edit_button = QPushButton("Edit Context")
    page.phase14_context_edit_button.setMinimumHeight(38)
    set_button_icon(page.phase14_context_edit_button, "pen-tool", size=17)
    summary_row.addWidget(page.phase14_context_edit_button)
    context.addLayout(summary_row)

    page.phase14_context_controls_panel = QWidget()
    controls = QHBoxLayout(page.phase14_context_controls_panel)
    controls.setContentsMargins(0, 8, 0, 1)
    controls.setSpacing(8)
    for title, icon_name, attribute in _CONTEXT_FIELDS:
        control = getattr(page, attribute)
        control.show()
        controls.addWidget(_field(title, control, icon_name=icon_name), 1)
    page.phase14_context_controls_panel.hide()
    context.addWidget(page.phase14_context_controls_panel)

    page.phase14_context_edit_button.clicked.connect(lambda: _toggle_context_controls(page))
    _refresh_context_summary(page)
    return context


def _build_intent_card(page) -> FoundryCard:
    intent_card = FoundryCard("Rotation Intent", "rotations")
    intent_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    intent_card.addWidget(_muted("Choose a focus. FoundryDock configures sensible defaults, which you can adjust."))

    intent_buttons = QHBoxLayout()
    intent_buttons.setSpacing(8)
    page.phase14_intent_buttons = {}
    for name, values in _INTENTS.items():
        button = QPushButton(f"{name}\n{values['description']}")
        button.setCheckable(True)
        button.setMinimumHeight(98)
        button.setMaximumHeight(104)
        button.setProperty("rotationIntentChoice", True)
        set_button_icon(button, values["icon"], size=28)
        button.clicked.connect(lambda checked, intent=name: _apply_intent(page, intent) if checked else None)
        page.phase14_intent_buttons[name] = button
        intent_buttons.addWidget(button, 1)
    intent_card.addLayout(intent_buttons)

    generated_heading = QHBoxLayout()
    generated_heading.setContentsMargins(0, 4, 0, 2)
    generated_heading.addWidget(QLabel("Generated Settings"))
    generated_heading.addStretch(1)
    page.phase14_rotation_customized_label = QLabel("Preset defaults")
    page.phase14_rotation_customized_label.setProperty("cardBadge", True)
    generated_heading.addWidget(page.phase14_rotation_customized_label)
    page.phase14_rotation_reset_button = QPushButton("Reset to preset")
    page.phase14_rotation_reset_button.setVisible(False)
    set_button_icon(page.phase14_rotation_reset_button, "refresh", size=15)
    page.phase14_rotation_reset_button.clicked.connect(lambda: _apply_intent(page, page.phase14_rotation_intent))
    generated_heading.addWidget(page.phase14_rotation_reset_button)
    intent_card.addLayout(generated_heading)

    page.phase14_rotation_setting_labels = {
        name: QLabel() for name in ("Weaving", "Bar swapping", "Heavy attacks", "Resource reserve")
    }
    for name, value_label in page.phase14_rotation_setting_labels.items():
        intent_card.addWidget(_summary_row(name, value_label))

    page.phase14_rotation_advanced_panel = _build_advanced_panel(page)
    page.phase14_rotation_advanced_panel.hide()
    intent_card.addStretch(1)
    advanced_button = QPushButton("Advanced execution & sustain")
    advanced_button.setMinimumHeight(44)
    set_button_icon(advanced_button, "uptime", size=19)
    advanced_button.clicked.connect(
        lambda: page.phase14_rotation_advanced_panel.setVisible(not page.phase14_rotation_advanced_panel.isVisible())
    )
    intent_card.addWidget(advanced_button)
    intent_card.addWidget(page.phase14_rotation_advanced_panel)
    return intent_card


def _build_obligations_card(page) -> FoundryCard:
    obligations = FoundryCard("Inputs & Obligations", "field-office")
    obligations.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    obligations.addWidget(_muted("Detected from your build, team setup, and encounter. Review and adjust."))
    page.phase14_obligation_count_labels = {}

    priority_host = QWidget()
    priority_layout = QVBoxLayout(priority_host)
    priority_layout.setContentsMargins(8, 4, 8, 8)
    page.priority_table.setMinimumHeight(210)
    priority_layout.addWidget(page.priority_table)

    pressure_host = QWidget()
    pressure_layout = QVBoxLayout(pressure_host)
    pressure_layout.setContentsMargins(8, 4, 8, 8)
    page.rotation_pressure_table.setMinimumHeight(170)
    pressure_layout.addWidget(page.rotation_pressure_table)

    obligations.addWidget(_obligation_row(page, "Build skills", "Saved bars, passives, and priorities.", str(_skill_count(page)), priority_host))
    obligations.addWidget(_obligation_row(page, "Gear procs", "Reviewed active set and item proc rules.", "—"))
    obligations.addWidget(_obligation_row(page, "Team duties", "Group buffs, synergies, and assignments.", "—"))
    obligations.addWidget(_obligation_row(page, "Pressure windows", "Short high-intensity encounter windows.", str(_pressure_count(page)), pressure_host))
    obligations.addWidget(_obligation_row(page, "Advanced rules", "Priority and conditional logic.", "—", _build_rules_detail()))

    obligations.addStretch(1)
    page.generate_button.setMinimumHeight(60)
    page.generate_button.setMaximumHeight(64)
    set_button_icon(page.generate_button, "rotations", size=22)
    obligations.addWidget(page.generate_button)
    return obligations


def _build_setup_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    layout.addWidget(_build_context(page))

    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(10)
    columns.addWidget(_build_intent_card(page), 4)
    columns.addWidget(_build_obligations_card(page), 3)
    layout.addLayout(columns, 1)
    return tab


def _configure_result_tabs(page) -> None:
    tabs = page.rotation_builder_tabs
    if tabs.count() > 0:
        tabs.setTabText(0, "Builder")
        builder_icon = icon("rotations")
        if not builder_icon.isNull():
            tabs.setTabIcon(0, builder_icon)
    for index, label, icon_name in _RESULT_TABS:
        if index >= tabs.count():
            continue
        tabs.setTabText(index, label)
        tab_icon = icon(icon_name)
        if not tab_icon.isNull():
            tabs.setTabIcon(index, tab_icon)


def _enable_result_tabs(page, enabled: bool) -> None:
    tabs = page.rotation_builder_tabs
    for index in range(1, tabs.count()):
        tabs.setTabEnabled(index, enabled)


def _refresh_phase14_state(page) -> None:
    if hasattr(page, "phase14_intent_buttons") and not getattr(page, "phase14_rotation_intent", ""):
        _apply_intent(page, "Safe Progression")
    _refresh_setting_summary(page)
    _refresh_obligation_counts(page)
    _refresh_context_summary(page)
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

    _configure_result_tabs(page)

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
        page.rotation_goal_combo,
        page.rotation_la_reliability_combo,
        page.rotation_bar_swap_comfort_combo,
        page.rotation_heavy_behavior_combo,
        page.rotation_complexity_combo,
        page.rotation_minimum_reserve_spin,
        page.rotation_prioritize_survival,
    ):
        if hasattr(control, "currentTextChanged"):
            control.currentTextChanged.connect(lambda _value: _refresh_setting_summary(page))
        if hasattr(control, "valueChanged"):
            control.valueChanged.connect(lambda _value: _refresh_setting_summary(page))
        if hasattr(control, "toggled"):
            control.toggled.connect(lambda _value: _refresh_setting_summary(page))

    for signal_owner in (
        page.character_combo,
        page.build_combo,
        page.rotation_team_combo,
        page.rotation_content_combo,
        page.rotation_boss_combo,
        page.rotation_threshold_difficulty_combo,
    ):
        signal_owner.currentIndexChanged.connect(lambda _i: (_refresh_context_summary(page), _refresh_obligation_counts(page)))

    _refresh_phase14_state(page)
    page._phase14_rotation_command_center_installed = True


__all__ = ["install_phase14_rotation_command_center"]
