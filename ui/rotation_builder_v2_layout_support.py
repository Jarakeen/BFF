from __future__ import annotations

"""Intent-first Rotation Builder workspace.

The V2 UI reorganizes the existing canonical Rotation machinery instead of replacing it.
Existing planner, timeline, sustain, export, artifact, and encounter controls remain the
authority. New controls that do not yet have production engine semantics are clearly
presentation/workspace inputs and never pretend to affect Generate.
"""

from types import MethodType

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

from engine.config import get_data_dir
from services.build_rotation_artifact_service import (
    BuildRotationArtifactService,
    resolve_canonical_build_id,
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
        "Choose whether Generate may rely on Light Attack weaving. 'Do not rely on it' "
        "turns Light Attack weaving off in the production generation request."
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

    page.rotation_prioritize_survival = QCheckBox(
        "Prioritize survivability over perfect output"
    )
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
            "General sustain and short high-drain pressure windows are separate concerns. "
            "Pressure-window reserve planning will use the same canonical resource engine."
        )
    )
    return card


def _build_style_card(page) -> FoundryCard:
    card = FoundryCard("Rotation Style", "◆").set_watermark("compass", 0.035)
    card.addWidget(_field(page, "ROTATION TYPE", page.rotation_type_combo))
    card.addWidget(
        _muted(
            "Static = fixed sequence. Semi-static = stable core with intelligent refreshes. "
            "Dynamic = priority/condition driven. Unsupported planner modes remain disabled."
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
    row = QHBoxLayout()
    row.addWidget(_field(page, "ROTATION GOAL", page.rotation_goal_combo), 1)
    row.addWidget(page._labelled_value("SAVED FOOD", page.food_value), 1)
    card.addLayout(row)
    card.addWidget(page.build_summary)
    card.addWidget(
        _muted(
            "Character, Build, Content, and Boss remain in the page header. Boss Context "
            "Variants resolve over the saved parent build before rotation evaluation."
        )
    )
    return card


def _build_rules_card(page) -> FoundryCard:
    card = FoundryCard("Rotation Rules & Requirements", "☷").set_watermark("compass", 0.035)
    page.rotation_rules_hint = _muted(
        "Ability priorities are live generation inputs. Gear-proc obligations, team "
        "assignments, required Heavy Attacks, and custom cadence rules will compose into "
        "this same rule surface as their canonical bridges are promoted."
    )
    card.addWidget(page.rotation_rules_hint)
    page.priority_table.setMinimumHeight(230)
    card.addWidget(page.priority_table)
    return card


def _add_pressure_row(page) -> None:
    row = page.rotation_pressure_table.rowCount()
    page.rotation_pressure_table.insertRow(row)
    for column, value in enumerate(("Custom pressure window", "", "6s", "High")):
        page.rotation_pressure_table.setItem(row, column, QTableWidgetItem(value))


def _remove_pressure_row(page) -> None:
    row = page.rotation_pressure_table.currentRow()
    if row >= 0:
        page.rotation_pressure_table.removeRow(row)


def _build_pressure_card(page) -> FoundryCard:
    card = FoundryCard("Pressure Windows", "⚑").set_watermark("compass", 0.035)
    card.addWidget(
        _muted(
            "Short intense windows such as Sunspire Ice Cages belong here: output demand, "
            "duration, recovery availability, and the reserve required before the window."
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
    card.addWidget(
        _muted(
            "Custom rows are workspace drafts until the pressure-window obligation contract "
            "is promoted into the planner; they are never silently treated as combat truth."
        )
    )
    return card


def _build_results_card(page) -> FoundryCard:
    card = FoundryCard("Generate & Results", "▶").set_watermark("compass", 0.035)
    row = QHBoxLayout()
    row.addWidget(page.generate_button)
    row.addWidget(page.clear_plan_button)
    row.addStretch()
    card.addLayout(row)
    page.rotation_result_hint = _muted(
        "Generate uses the implemented planner and live canonical evidence. Timeline, "
        "resource evidence, explanations, comparison, and export live in the tabs above."
    )
    card.addWidget(page.rotation_result_hint)
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
    for column in range(3):
        grid.setColumnStretch(column, 1)

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

    visual = FoundryCard("Rotation Timeline", "◇").set_watermark("compass", 0.035)
    page.rotation_timeline_widget.setMinimumHeight(300)
    visual.addWidget(page.rotation_timeline_widget)
    visual.addWidget(
        _muted(
            "Ability icons come from the packaged assets/AbilityIcons icon library through "
            "the existing timeline icon resolver; missing icons remain explicit evidence."
        )
    )
    layout.addWidget(visual)

    details = FoundryCard("Rotation Actions (in order)", "☷").set_watermark("compass", 0.03)
    page.timeline_table.setVisible(True)
    page.timeline_table.setMinimumHeight(260)
    details.addWidget(page.timeline_table)
    details.addWidget(page.timeline_hint)
    layout.addWidget(details)
    return tab


def _build_resources_tab(page) -> QWidget:
    tab = QWidget()
    layout = QGridLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.setColumnStretch(0, 2)
    layout.setColumnStretch(1, 1)

    sustain = FoundryCard("Resource Graphs", "◈").set_watermark("compass", 0.04)
    sustain.addWidget(page.sustain_graph)
    sustain.addWidget(page.resource_summary)
    sustain.addWidget(page.resource_detail)
    layout.addWidget(sustain, 0, 0)

    duration = FoundryCard("Duration & Uptime Evidence", "◆").set_watermark("compass", 0.035)
    duration.addWidget(page.duration_evidence_card)
    layout.addWidget(duration, 0, 1)

    cadence = getattr(page, "cadence_progression_card", None)
    if cadence is not None:
        layout.addWidget(cadence, 1, 0, 1, 2)
    return tab


def _build_explanations_tab(page) -> QWidget:
    tab = QWidget()
    grid = QGridLayout(tab)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(8)
    grid.setColumnStretch(0, 2)
    grid.setColumnStretch(1, 1)

    explanation = FoundryCard("Rotation Explanation", "◇").set_watermark("compass", 0.035)
    page.rotation_explanation_label = QLabel("Generate a rotation to see its assumptions and unresolved decisions.")
    page.rotation_explanation_label.setWordWrap(True)
    page.rotation_explanation_label.setTextInteractionFlags(
        page.rotation_explanation_label.textInteractionFlags()
        | page.rotation_explanation_label.textInteractionFlags().__class__.TextSelectableByMouse
    )
    explanation.addWidget(page.rotation_explanation_label)
    grid.addWidget(explanation, 0, 0)

    notes = FoundryCard("Notes", "✎").set_watermark("feather", 0.05)
    page.notes_edit.setMaximumHeight(220)
    notes.addWidget(page.notes_edit)
    grid.addWidget(notes, 0, 1)
    return tab


def _metric(plan, artifact, metric: str) -> str:
    if plan is not None:
        if metric == "Duration":
            return f"{float(plan.duration_seconds):g}s"
        if metric == "Total Actions":
            return str(len(tuple(plan.actions or ())))
        if metric == "Assumptions":
            return str(len(tuple(plan.assumptions or ())))
        if metric == "Unresolved":
            return str(len(tuple(plan.unresolved or ())))
    if isinstance(artifact, dict):
        if metric == "Duration":
            return f"{float(artifact.get('duration_seconds') or 0):g}s"
        if metric == "Total Actions":
            return str(len(artifact.get("actions") or []))
        if metric == "Assumptions":
            return str(len(artifact.get("assumptions") or []))
        if metric == "Unresolved":
            return str(len(artifact.get("unresolved") or []))
    return "—"


def _refresh_compare(page) -> None:
    table = page.rotation_compare_table
    current_plan = getattr(page, "rotation_plan", None)
    build = page._selected_build()
    service = BuildRotationArtifactService(get_data_dir() / "build_rotations.json")
    current_artifact = None
    if build is not None:
        build_id = resolve_canonical_build_id(page.build_service.canonical.catalog_service, build)
        if build_id:
            current_artifact = service.get_rotation(build_id)

    alternate_artifact = page.rotation_compare_build_combo.currentData()
    metrics = ("Duration", "Total Actions", "Assumptions", "Unresolved")
    table.setRowCount(len(metrics))
    for row, metric in enumerate(metrics):
        values = (
            metric,
            _metric(current_plan, None, metric),
            _metric(None, current_artifact, metric),
            _metric(None, alternate_artifact, metric),
        )
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))


def _populate_compare_builds(page) -> None:
    combo = page.rotation_compare_build_combo
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("Select saved rotation", None)
    service = BuildRotationArtifactService(get_data_dir() / "build_rotations.json")
    for build in page.roster.Members:
        build_id = resolve_canonical_build_id(page.build_service.canonical.catalog_service, build)
        if not build_id:
            continue
        artifact = service.get_rotation(build_id)
        if not artifact:
            continue
        character = str(getattr(build, "Name", "") or "Unnamed")
        build_name = str(getattr(build, "BuildName", "") or "Build")
        combo.addItem(f"{character} • {build_name}", artifact)
    combo.blockSignals(False)
    _refresh_compare(page)


def _build_compare_tab(page) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    controls = FoundryCard("Compare Rotations", "◇").set_watermark("compass", 0.035)
    row = QHBoxLayout()
    page.rotation_compare_build_combo = QComboBox()
    page.rotation_compare_build_combo.setMinimumWidth(280)
    row.addWidget(_field(page, "ALTERNATE SAVED ROTATION", page.rotation_compare_build_combo), 1)
    refresh = QPushButton("Refresh")
    refresh.clicked.connect(lambda: _populate_compare_builds(page))
    row.addWidget(refresh)
    controls.addLayout(row)
    layout.addWidget(controls)

    result = FoundryCard("Comparison", "☷").set_watermark("compass", 0.03)
    page.rotation_compare_table = QTableWidget(0, 4)
    page.rotation_compare_table.setHorizontalHeaderLabels(
        ["Metric", "Current Generated", "Current Saved", "Alternate Saved"]
    )
    page.rotation_compare_table.verticalHeader().setVisible(False)
    page.rotation_compare_table.horizontalHeader().setStretchLastSection(True)
    page.rotation_compare_table.setMinimumHeight(300)
    result.addWidget(page.rotation_compare_table)
    result.addWidget(
        _muted(
            "Comparison reports only evidence actually persisted on saved rotations. "
            "Resource and uptime metrics are not invented when older artifacts lack them."
        )
    )
    layout.addWidget(result)
    page.rotation_compare_build_combo.currentIndexChanged.connect(lambda _i: _refresh_compare(page))
    return tab


def _proxy_save(page) -> None:
    button = getattr(page, "save_rotation_to_build_button", None)
    if button is None:
        page.status.warning("Build-owned rotation saving is not installed in this app session.")
        return
    button.click()


def _proxy_export(page) -> None:
    exporter = getattr(page, "export_current_rotation_pdf", None)
    if callable(exporter):
        exporter()
        return
    page.status.warning("Rotation PDF export is not available in this app session.")


def _build_save_export_tab(page) -> QWidget:
    tab = QWidget()
    grid = QGridLayout(tab)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(8)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)

    save = FoundryCard("Save Rotation", "◆").set_watermark("compass", 0.035)
    save.addWidget(
        _muted(
            "Save the completed plan to the exact canonical build dossier. Saving again "
            "replaces only that build's previous rotation artifact."
        )
    )
    page.rotation_v2_save_button = QPushButton("Save Rotation")
    page.rotation_v2_save_button.setProperty("primary", True)
    page.rotation_v2_save_button.clicked.connect(lambda: _proxy_save(page))
    save.addWidget(page.rotation_v2_save_button)
    grid.addWidget(save, 0, 0)

    export = FoundryCard("Export Options", "✦").set_watermark("feather", 0.04)
    export.addWidget(
        _muted(
            "Export uses the existing phone-readable PDF timeline renderer, including the "
            "materialized timeline projection, sustain summary, build context, and notes."
        )
    )
    page.rotation_v2_export_pdf_button = QPushButton("Export PDF")
    page.rotation_v2_export_pdf_button.clicked.connect(lambda: _proxy_export(page))
    export.addWidget(page.rotation_v2_export_pdf_button)
    grid.addWidget(export, 0, 1)
    return tab


def _refresh_explanations(page) -> None:
    plan = getattr(page, "rotation_plan", None)
    if plan is None:
        page.rotation_explanation_label.setText(
            "Generate a rotation to see its assumptions and unresolved decisions."
        )
        return
    lines = ["WHY THIS ROTATION", ""]
    assumptions = tuple(getattr(plan, "assumptions", ()) or ())
    unresolved = tuple(getattr(plan, "unresolved", ()) or ())
    if assumptions:
        lines.append("Assumptions")
        lines.extend(f"• {item}" for item in assumptions)
    if unresolved:
        lines.extend(("", "Warnings / unresolved"))
        lines.extend(f"• {item}" for item in unresolved)
    if not assumptions and not unresolved:
        lines.append("No schedule-level assumptions or unresolved items were reported.")
    page.rotation_explanation_label.setText("\n".join(lines))


def _install_result_refresh(page) -> None:
    original_set_plan = page.set_rotation_plan
    original_clear_plan = page.clear_rotation_plan

    def set_plan_v2(plan) -> None:
        original_set_plan(plan)
        _refresh_explanations(page)
        _refresh_compare(page)
        page.rotation_v2_save_button.setEnabled(bool(plan and tuple(plan.actions or ())))
        page.rotation_v2_export_pdf_button.setEnabled(bool(plan and tuple(plan.actions or ())))

    def clear_plan_v2(*, refresh: bool = True) -> None:
        original_clear_plan(refresh=refresh)
        _refresh_explanations(page)
        _refresh_compare(page)
        page.rotation_v2_save_button.setEnabled(False)
        page.rotation_v2_export_pdf_button.setEnabled(False)

    page.set_rotation_plan = set_plan_v2
    page.clear_rotation_plan = clear_plan_v2


def install_rotation_builder_v2_layout(page) -> None:
    """Replace the legacy dashboard arrangement with the six-tab V2 workspace."""
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
    page.rotation_builder_tabs.addTab(_build_compare_tab(page), "Compare")
    page.rotation_builder_tabs.addTab(_build_save_export_tab(page), "Save / Export")

    _install_execution_contract(page)
    _install_result_refresh(page)
    page.rotation_builder_tabs.currentChanged.connect(
        lambda index: _populate_compare_builds(page)
        if page.rotation_builder_tabs.tabText(index) == "Compare"
        else None
    )

    page.workspace_layout.insertWidget(0, page.rotation_builder_tabs)
    if original_workspace is not None:
        original_workspace.hide()

    page.generate_button.setToolTip(
        "Generate from the selected build using the implemented planner, execution "
        "profile, and canonical evidence currently available."
    )
    page.rotation_v2_save_button.setEnabled(False)
    page.rotation_v2_export_pdf_button.setEnabled(False)
    _populate_compare_builds(page)
    _refresh_explanations(page)
    page._rotation_builder_v2_layout_installed = True


__all__ = ["install_rotation_builder_v2_layout"]
