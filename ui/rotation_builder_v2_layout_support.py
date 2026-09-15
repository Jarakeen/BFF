from __future__ import annotations

"""User-intent layout for Rotation Builder.

This layer deliberately reuses the dashboard's canonical widgets rather than cloning
engine inputs.  The new workspace organizes Rotation around build context, rotation
style, execution profile, sustain, pressure windows, and generated evidence while the
underlying planners continue to own combat truth.
"""

from types import MethodType

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


def _field(page, title: str, widget: QWidget) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    layout.addWidget(label)
    layout.addWidget(widget)
    return box


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def _build_execution_profile(page) -> FoundryCard:
    card = FoundryCard("Execution Profile", "◇").set_watermark("compass", 0.035)
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)

    page.rotation_la_reliability_combo = QComboBox()
    page.rotation_la_reliability_combo.addItems(
        ["Reliable", "Usually", "Inconsistent", "Do not rely on it"]
    )
    page.rotation_la_reliability_combo.setCurrentText("Usually")
    page.rotation_la_reliability_combo.setToolTip(
        "Controls whether generated rotations may rely on Light Attack weaving. "
        "The baseline planner currently treats all choices except 'Do not rely on it' "
        "as Light-Attack-capable; finer reliability modeling is a later engine layer."
    )

    page.rotation_bar_swap_comfort_combo = QComboBox()
    page.rotation_bar_swap_comfort_combo.addItems(
        ["Comfortable", "Prefer fewer swaps", "Minimize swaps"]
    )

    page.rotation_heavy_behavior_combo = QComboBox()
    page.rotation_heavy_behavior_combo.addItems(
        ["Use when needed", "Prefer safe windows", "Required only", "Avoid unless mandatory"]
    )

    page.rotation_complexity_combo = QComboBox()
    page.rotation_complexity_combo.addItems(["Simple", "Moderate", "High"])
    page.rotation_complexity_combo.setCurrentText("Moderate")

    page.rotation_prioritize_survival = QCheckBox("Prioritize survivability over perfect output")
    page.rotation_human_reaction_time = QCheckBox("Account for human reaction time")
    page.rotation_human_reaction_time.setChecked(True)

    grid.addWidget(_field(page, "LIGHT ATTACK WEAVING", page.rotation_la_reliability_combo), 0, 0)
    grid.addWidget(_field(page, "BAR SWAPPING", page.rotation_bar_swap_comfort_combo), 0, 1)
    grid.addWidget(_field(page, "HEAVY ATTACKS", page.rotation_heavy_behavior_combo), 1, 0)
    grid.addWidget(_field(page, "ROTATION COMPLEXITY", page.rotation_complexity_combo), 1, 1)
    grid.addWidget(page.rotation_prioritize_survival, 2, 0, 1, 2)
    grid.addWidget(page.rotation_human_reaction_time, 3, 0, 1, 2)
    card.addLayout(grid)
    return card


def _build_sustain_card(page) -> FoundryCard:
    card = FoundryCard("Sustain & Resources", "◈").set_watermark("compass", 0.04)
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)

    page.rotation_primary_resource_combo = QComboBox()
    page.rotation_primary_resource_combo.addItems(["Auto from build", "Magicka", "Stamina"])

    page.rotation_minimum_reserve_spin = QSpinBox()
    page.rotation_minimum_reserve_spin.setRange(0, 100)
    page.rotation_minimum_reserve_spin.setValue(20)
    page.rotation_minimum_reserve_spin.setSuffix("%")
    page.rotation_minimum_reserve_spin.setToolTip(
        "General reserve target. Pressure-window reserves may temporarily require more."
    )

    page.rotation_prepare_for_pressure = QCheckBox(
        "Prepare resources before known pressure windows"
    )
    page.rotation_prepare_for_pressure.setChecked(True)

    grid.addWidget(_field(page, "PRIMARY RESOURCE", page.rotation_primary_resource_combo), 0, 0)
    grid.addWidget(_field(page, "MINIMUM RESERVE", page.rotation_minimum_reserve_spin), 0, 1)
    grid.addWidget(_field(page, "ROTATION POTION", page.potion_combo), 1, 0, 1, 2)
    grid.addWidget(page.potion_on_cooldown, 2, 0, 1, 2)
    grid.addWidget(page.rotation_prepare_for_pressure, 3, 0, 1, 2)
    card.addLayout(grid)
    card.addWidget(
        _muted(
            "General sustain is always relevant. Encounter pressure can require a much "
            "higher reserve immediately before a short, expensive burst window."
        )
    )
    return card


def _build_style_card(page) -> FoundryCard:
    card = FoundryCard("Rotation Style", "◆").set_watermark("compass", 0.035)
    card.addWidget(_field(page, "ROTATION TYPE", page.rotation_type_combo))
    card.addWidget(
        _muted(
            "Static = fixed sequence. Semi-static = stable core with intelligent refreshes. "
            "Dynamic = priority/condition driven. The current production planner still "
            "enables Generate only for implemented modes."
        )
    )
    card.addWidget(_field(page, "EXECUTE STARTS", page.execute_spin))
    card.addWidget(_field(page, "TARGET TYPE", page.target_type_combo))
    return card


def _build_context_card(page) -> FoundryCard:
    card = FoundryCard("Build & Context", "✦").set_watermark("feather", 0.04)
    page.rotation_goal_combo = QComboBox()
    page.rotation_goal_combo.addItems(
        [
            "Progression / Difficult Content",
            "Sustainable",
            "Healing / Support",
            "Damage",
            "Parse / Dummy",
            "Custom",
        ]
    )
    card.addWidget(_field(page, "ROTATION GOAL", page.rotation_goal_combo))
    card.addWidget(page.build_summary)
    card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))
    card.addWidget(
        _muted(
            "Character, Build, Content, and Boss stay in the page header. Boss Context "
            "Variants are resolved as sparse overrides over the saved parent build."
        )
    )
    return card


def _build_rules_card(page) -> FoundryCard:
    card = FoundryCard("Rotation Rules & Requirements", "☷").set_watermark("compass", 0.035)
    card.addWidget(
        _muted(
            "Ability priorities are the first visible rule layer. Gear-proc obligations, "
            "team assignments, required Heavy Attacks, uptime rules, and user-authored "
            "requirements will compose here rather than becoming separate planners."
        )
    )
    page.priority_table.setMinimumHeight(240)
    card.addWidget(page.priority_table)
    return card


def _add_pressure_row(page) -> None:
    row = page.rotation_pressure_table.rowCount()
    page.rotation_pressure_table.insertRow(row)
    defaults = ("Custom pressure window", "", "6s", "High")
    for column, value in enumerate(defaults):
        page.rotation_pressure_table.setItem(row, column, QTableWidgetItem(value))


def _remove_pressure_row(page) -> None:
    row = page.rotation_pressure_table.currentRow()
    if row >= 0:
        page.rotation_pressure_table.removeRow(row)


def _build_pressure_card(page) -> FoundryCard:
    card = FoundryCard("Pressure Windows", "⚑").set_watermark("compass", 0.035)
    card.addWidget(
        _muted(
            "Short intense windows such as Ice Cages belong here: output demand, duration, "
            "recovery availability, and the resource reserve required before the window."
        )
    )

    page.rotation_pressure_table = QTableWidget(0, 4)
    page.rotation_pressure_table.setHorizontalHeaderLabels(
        ["Event", "Start / Trigger", "Duration", "Resource Impact"]
    )
    page.rotation_pressure_table.verticalHeader().setVisible(False)
    page.rotation_pressure_table.horizontalHeader().setStretchLastSection(True)
    page.rotation_pressure_table.setMinimumHeight(180)
    card.addWidget(page.rotation_pressure_table)

    row = QHBoxLayout()
    page.rotation_add_pressure_button = QPushButton("Add Custom Window")
    page.rotation_remove_pressure_button = QPushButton("Remove")
    page.rotation_add_pressure_button.clicked.connect(lambda: _add_pressure_row(page))
    page.rotation_remove_pressure_button.clicked.connect(lambda: _remove_pressure_row(page))
    row.addWidget(page.rotation_add_pressure_button)
    row.addWidget(page.rotation_remove_pressure_button)
    row.addStretch()
    card.addLayout(row)

    warning = _muted(
        "Custom rows are workspace drafts for now; they are not yet promoted into "
        "canonical planner obligations. Reviewed encounter windows will be wired here next."
    )
    warning.setProperty("warning", True)
    card.addWidget(warning)
    return card


def _build_results_card(page) -> FoundryCard:
    card = FoundryCard("Generate & Results", "▶").set_watermark("compass", 0.035)
    row = QHBoxLayout()
    row.addWidget(page.generate_button)
    row.addWidget(page.clear_plan_button)
    row.addStretch()
    card.addLayout(row)
    card.addWidget(page.resource_summary)
    card.addWidget(page.resource_detail)
    return card


def _install_execution_contract(page) -> None:
    def weave_light_attacks(bound_page) -> bool:
        return bound_page.rotation_la_reliability_combo.currentText() != "Do not rely on it"

    page.rotation_weave_light_attacks = MethodType(weave_light_attacks, page)


def _build_builder_tab(page) -> QWidget:
    tab = QWidget()
    grid = QGridLayout(tab)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 1)

    grid.addWidget(_build_context_card(page), 0, 0, 1, 3)
    grid.addWidget(_build_style_card(page), 1, 0)
    grid.addWidget(_build_execution_profile(page), 1, 1)
    grid.addWidget(_build_sustain_card(page), 1, 2)
    grid.addWidget(_build_rules_card(page), 2, 0, 1, 2)
    grid.addWidget(_build_pressure_card(page), 2, 2)
    grid.addWidget(_build_results_card(page), 3, 0, 1, 3)
    return tab


def _build_timeline_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    card = FoundryCard("Rotation Timeline", "◇").set_watermark("compass", 0.035)
    page.timeline_table.setMinimumHeight(420)
    card.addWidget(page.timeline_table)
    card.addWidget(page.timeline_hint)
    layout.addWidget(card)
    return tab


def _build_resources_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    card = FoundryCard("Uptime & Resources", "◈").set_watermark("compass", 0.04)
    card.addWidget(page.sustain_graph)
    card.addWidget(page.resource_summary)
    card.addWidget(page.resource_detail)
    layout.addWidget(card)
    layout.addWidget(page.duration_evidence_card)
    return tab


def _build_explanations_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    notes = FoundryCard("Notes & Explanations", "✎").set_watermark("feather", 0.05)
    page.notes_edit.setMaximumHeight(180)
    notes.addWidget(page.notes_edit)
    layout.addWidget(notes)
    cadence = getattr(page, "cadence_progression_card", None)
    if cadence is not None:
        layout.addWidget(cadence)
    return tab


def install_rotation_builder_v2_layout(page) -> None:
    """Replace the legacy dashboard arrangement with the intent-first workspace."""
    if bool(getattr(page, "_rotation_builder_v2_layout_installed", False)):
        return

    original_item = page.workspace_layout.itemAt(0)
    original_workspace = original_item.widget() if original_item is not None else None

    page.rotation_builder_tabs = QTabWidget()
    page.rotation_builder_tabs.setDocumentMode(True)
    page.rotation_builder_tabs.addTab(_build_builder_tab(page), "Builder")
    page.rotation_builder_tabs.addTab(_build_timeline_tab(page), "Timeline")
    page.rotation_builder_tabs.addTab(_build_resources_tab(page), "Uptime & Resources")
    page.rotation_builder_tabs.addTab(_build_explanations_tab(page), "Explanations")

    _install_execution_contract(page)
    page.workspace_layout.insertWidget(0, page.rotation_builder_tabs)
    if original_workspace is not None:
        original_workspace.hide()

    page.generate_button.setToolTip(
        "Generate from the selected build using the implemented planner, execution "
        "profile, and canonical evidence currently available."
    )
    page._rotation_builder_v2_layout_installed = True


__all__ = ["install_rotation_builder_v2_layout"]
