from __future__ import annotations

"""Final polish/wiring for the Rotation Builder V2 workspace.

This layer intentionally does not claim Static/Dynamic planner support or completed
pressure-window planning. It finishes the user-facing V2 shell, wires execution-profile
Light Attack preference into the real generation request, and lets explicit Magicka /
Stamina selection control which sustain projection is shown. Existing canonical services
remain the authority for rotation, resource, timeline, save, and export behavior.
"""

from dataclasses import replace
from types import MethodType

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind
from ui.components.foundry_card import FoundryCard


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def _finish_header(page) -> None:
    page.header.title.setText("Rotation Builder")
    page.header.subtitle.setText("Build smarter. Play longer. Survive the hard parts.")
    page.header.department.setText("RAID ENGINE • ROTATIONS")


def _finish_tabs(page) -> None:
    tabs = page.rotation_builder_tabs
    tabs.setDocumentMode(True)
    tabs.setMovable(False)
    tabs.setUsesScrollButtons(False)
    tabs.setProperty("workspaceTabs", True)


def _finish_rotation_style(page) -> None:
    card = _card(page, "Rotation Style")
    if card is None or bool(getattr(page, "_rotation_mode_tiles_installed", False)):
        return

    wrapper = page.rotation_type_combo.parentWidget()
    if wrapper is not None:
        wrapper.hide()

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    page.rotation_mode_buttons = {}

    descriptions = {
        "Static": "Fixed sequence\nComing later",
        "Semi-static": "Core loop + smart refreshes\nAvailable",
        "Dynamic": "Priority / condition driven\nComing later",
    }
    for mode in ("Static", "Semi-static", "Dynamic"):
        button = QPushButton(f"{mode}\n{descriptions[mode]}")
        button.setCheckable(True)
        button.setProperty("rotationModeTile", True)
        button.setMinimumHeight(66)
        enabled = mode == "Semi-static"
        button.setEnabled(enabled)
        button.setChecked(mode == page.rotation_type_combo.currentText())
        if enabled:
            button.clicked.connect(
                lambda checked=False, value=mode: page.rotation_type_combo.setCurrentText(value)
            )
        row.addWidget(button, 1)
        page.rotation_mode_buttons[mode] = button

    def sync_mode(value: str) -> None:
        for mode, button in page.rotation_mode_buttons.items():
            button.setChecked(mode == value)

    page.rotation_type_combo.currentTextChanged.connect(sync_mode)
    card.body_layout.insertLayout(0, row)
    page._rotation_mode_tiles_installed = True


def _finish_rules_surface(page) -> None:
    card = _card(page, "Rotation Rules & Requirements")
    if card is None or bool(getattr(page, "_rotation_rules_tabs_installed", False)):
        return

    page.rotation_rules_tabs = QTabWidget()
    page.rotation_rules_tabs.setDocumentMode(True)
    page.rotation_rules_tabs.setUsesScrollButtons(False)

    build_tab = QWidget()
    build_layout = QVBoxLayout(build_tab)
    build_layout.setContentsMargins(0, 0, 0, 0)
    build_layout.setSpacing(4)
    page.priority_table.setParent(build_tab)
    build_layout.addWidget(page.priority_table)
    page.rotation_rules_tabs.addTab(build_tab, "Detected from Build")

    team_tab = QWidget()
    team_layout = QVBoxLayout(team_tab)
    team_layout.setContentsMargins(8, 8, 8, 8)
    team_layout.addWidget(
        _muted(
            "Team-owned requirements will appear here when Rotation receives resolved "
            "Raid Plan / Assignment provider context. Nothing is inferred from role alone."
        )
    )
    team_layout.addStretch()
    page.rotation_rules_tabs.addTab(team_tab, "Team Assignments")

    encounter_tab = QWidget()
    encounter_layout = QVBoxLayout(encounter_tab)
    encounter_layout.setContentsMargins(8, 8, 8, 8)
    encounter_layout.addWidget(
        _muted(
            "Reviewed encounter obligations appear here when canonical encounter evidence "
            "exists. Missing encounter research does not fabricate requirements."
        )
    )
    encounter_layout.addStretch()
    page.rotation_rules_tabs.addTab(encounter_tab, "Encounter Windows")

    custom_tab = QWidget()
    custom_layout = QVBoxLayout(custom_tab)
    custom_layout.setContentsMargins(8, 8, 8, 8)
    custom_layout.addWidget(
        _muted(
            "Custom cadence rules such as 'Heavy Attack twice every 20 seconds' belong here. "
            "The editor is visible as the V2 destination while its canonical obligation bridge is completed."
        )
    )
    custom_layout.addStretch()
    page.rotation_rules_tabs.addTab(custom_tab, "Custom Rules")

    card.addWidget(page.rotation_rules_tabs)
    page._rotation_rules_tabs_installed = True


def _wire_light_attack_profile(page) -> None:
    generation = page.rotation_generation
    if bool(getattr(generation, "_rotation_v2_execution_profile_installed", False)):
        return

    original_generate_with_evidence = generation.generate_with_evidence

    def generate_with_profile(_service, *, build, request):
        resolver = getattr(page, "rotation_weave_light_attacks", None)
        weave = bool(resolver()) if callable(resolver) else bool(request.weave_light_attacks)
        return original_generate_with_evidence(
            build=build,
            request=replace(request, weave_light_attacks=weave),
        )

    generation.generate_with_evidence = MethodType(generate_with_profile, generation)
    generation._rotation_v2_execution_profile_installed = True


def _wire_resource_selection(page) -> None:
    sustain = page.rotation_sustain
    if bool(getattr(sustain, "_rotation_v2_resource_selection_installed", False)):
        return

    original_evaluate = sustain.evaluate

    def evaluate_selected_resource(_service, *args, **kwargs):
        selected = str(page.rotation_primary_resource_combo.currentText() or "").strip()
        if selected == "Magicka":
            kwargs["resource"] = ResourceType.MAGICKA
        elif selected == "Stamina":
            kwargs["resource"] = ResourceType.STAMINA
        return original_evaluate(*args, **kwargs)

    sustain.evaluate = MethodType(evaluate_selected_resource, sustain)
    sustain._rotation_v2_resource_selection_installed = True


def _result_text(plan) -> str:
    if plan is None:
        return "Generate a rotation to populate the summary."
    actions = tuple(getattr(plan, "actions", ()) or ())
    heavy_count = sum(
        1
        for action in actions
        if getattr(action, "kind", None) is RotationActionKind.HEAVY_ATTACK
    )
    unresolved = len(tuple(getattr(plan, "unresolved", ()) or ()))
    return (
        f"{float(getattr(plan, 'duration_seconds', 0.0)):g}s  •  "
        f"{len(actions)} actions  •  {heavy_count} Heavy Attacks  •  "
        f"{unresolved} unresolved"
    )


def _finish_results_card(page) -> None:
    card = _card(page, "Generate & Results")
    if card is None or bool(getattr(page, "_rotation_result_summary_installed", False)):
        return

    page.rotation_v2_result_summary = QLabel(_result_text(getattr(page, "rotation_plan", None)))
    page.rotation_v2_result_summary.setWordWrap(True)
    page.rotation_v2_result_summary.setProperty("resultSummary", True)
    card.addWidget(page.rotation_v2_result_summary)

    original_set_plan = page.set_rotation_plan
    original_clear_plan = page.clear_rotation_plan

    def set_plan_with_summary(plan) -> None:
        original_set_plan(plan)
        page.rotation_v2_result_summary.setText(_result_text(plan))

    def clear_plan_with_summary(*, refresh: bool = True) -> None:
        original_clear_plan(refresh=refresh)
        page.rotation_v2_result_summary.setText(_result_text(None))

    page.set_rotation_plan = set_plan_with_summary
    page.clear_rotation_plan = clear_plan_with_summary
    page._rotation_result_summary_installed = True


def _finish_pressure_card(page) -> None:
    card = _card(page, "Pressure Windows")
    if card is None:
        return
    card.set_badge("PLANNING")
    page.rotation_pressure_table.setToolTip(
        "Pressure-window UI is intentionally visible for encounter planning, but its "
        "planner obligation bridge is still under construction."
    )


def _finish_compare_table(page) -> None:
    table = getattr(page, "rotation_compare_table", None)
    if not isinstance(table, QTableWidget):
        return
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)


def install_rotation_builder_v2_finish(page) -> None:
    """Finish the testable V2 presentation without claiming unfinished planner semantics."""
    if bool(getattr(page, "_rotation_builder_v2_finish_installed", False)):
        return

    _finish_header(page)
    _finish_tabs(page)
    _finish_rotation_style(page)
    _finish_rules_surface(page)
    _wire_light_attack_profile(page)
    _wire_resource_selection(page)
    _finish_results_card(page)
    _finish_pressure_card(page)
    _finish_compare_table(page)

    page.rotation_la_reliability_combo.setToolTip(
        "Reliable / Usually / Inconsistent currently permit Light Attack weaving; "
        "Do not rely on it removes Light Attacks from the generated baseline rotation."
    )
    page.rotation_minimum_reserve_spin.setToolTip(
        "Visible V2 sustain target. Automatic reserve-driven Heavy Attack scheduling is "
        "being finished separately from the encounter-aware advanced mode."
    )
    page._rotation_builder_v2_finish_installed = True


__all__ = ["install_rotation_builder_v2_finish"]
