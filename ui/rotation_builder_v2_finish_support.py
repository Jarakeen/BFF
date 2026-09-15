from __future__ import annotations

"""Final polish/wiring for the Rotation Builder V2 workspace.

This layer intentionally does not claim Static/Dynamic planner support or completed
pressure-window planning. It finishes the user-facing V2 shell and bridges the pieces
that are already real: sparse Boss build inheritance, execution-profile Light Attack
preference, build-aware recovery Heavy Attack stabilization, and explicit resource
selection. Existing canonical services remain the authority for game mechanics.
"""

from dataclasses import replace
from types import MethodType

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationActionKind
from services.build_context_variant_service import resolve_build_context
from services.rotation_heavy_sustain_projection_service import (
    RotationHeavySustainProjectionService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.components.foundry_card import FoundryCard
from ui.rotation_dashboard_page import RotationDashboardPage
from ui.rotation_generation_support import RotationGenerationResult


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
    for index in range(tabs.count()):
        if tabs.tabText(index) == "Uptime_Resources":
            tabs.setTabText(index, "Uptime && Resources")


def _remove_header_wrapper(page, control) -> None:
    wrapper = control.parentWidget()
    layout = getattr(page.header, "context_layout", None)
    if wrapper is None or layout is None:
        return
    for index in range(layout.count() - 1, -1, -1):
        item = layout.itemAt(index)
        if item is not None and item.widget() is wrapper:
            layout.takeAt(index)
            control.setParent(page)
            wrapper.setParent(None)
            wrapper.deleteLater()
            return


def _move_context_to_top_card(page) -> None:
    card = _card(page, "Build & Context")
    if card is None or bool(getattr(page, "_rotation_context_card_controls_installed", False)):
        return

    controls = (
        ("CHARACTER", page.character_combo),
        ("BUILD", page.build_combo),
        ("CONTENT", page.rotation_content_combo),
        ("BOSS", page.rotation_boss_combo),
        ("DIFFICULTY", page.rotation_threshold_difficulty_combo),
    )
    for _title, control in controls:
        _remove_header_wrapper(page, control)
        control.show()

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    for column in range(5):
        grid.setColumnStretch(column, 1)
    for column, (title, control) in enumerate(controls):
        grid.addWidget(page._context_field(title, control), 0, column)

    card.body_layout.insertLayout(0, grid)
    page._rotation_context_card_controls_installed = True


def _boss_name(page) -> str:
    combo = getattr(page, "rotation_boss_combo", None)
    if combo is None:
        return ""
    return str(combo.currentText() or "").strip()


def _install_effective_boss_build_scope(page) -> None:
    """Use sparse Boss variants only while Rotation is reading/evaluating the build.

    Rotation artifacts must still save against the canonical parent build identity, so
    the ordinary ``_selected_build`` behavior remains the default outside refresh and
    Generate scopes.
    """
    if bool(getattr(page, "_rotation_effective_boss_scope_installed", False)):
        return

    base_selected_build = page._selected_build
    page._rotation_base_selected_build = base_selected_build
    page._rotation_effective_scope_active = False

    def effective_build(bound_page):
        base = base_selected_build()
        if base is None:
            return None
        boss = _boss_name(bound_page)
        if not boss:
            return base
        return resolve_build_context(base, boss_name=boss)

    def selected_build(bound_page):
        if bool(getattr(bound_page, "_rotation_effective_scope_active", False)):
            return effective_build(bound_page)
        return base_selected_build()

    page.rotation_effective_build = MethodType(effective_build, page)
    page._selected_build = MethodType(selected_build, page)

    def run_effective(callback):
        page._rotation_effective_scope_active = True
        try:
            return callback()
        finally:
            page._rotation_effective_scope_active = False

    page._run_in_rotation_effective_scope = run_effective

    def refresh_effective(*_args) -> None:
        run_effective(page._refresh_build_context)

    page.rotation_boss_combo.currentIndexChanged.connect(refresh_effective)
    page.build_combo.currentIndexChanged.connect(refresh_effective)

    try:
        page.generate_button.clicked.disconnect()
    except (RuntimeError, TypeError):
        pass

    def generate_effective() -> None:
        support = getattr(page, "rotation_generate_action_support", None)
        if support is not None:
            run_effective(lambda: support.generate(page))
        else:
            run_effective(lambda: RotationDashboardPage.generate_rotation(page))

    page.generate_button.clicked.connect(generate_effective)
    page._rotation_effective_boss_scope_installed = True
    refresh_effective()


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


def _primary_resource(page, static_context, initial_bar: str) -> ResourceType:
    selected = str(page.rotation_primary_resource_combo.currentText() or "").strip()
    if selected == "Magicka":
        return ResourceType.MAGICKA
    if selected == "Stamina":
        return ResourceType.STAMINA

    magicka = static_context.maximum_amount_for(initial_bar, ResourceType.MAGICKA)
    stamina = static_context.maximum_amount_for(initial_bar, ResourceType.STAMINA)
    return ResourceType.MAGICKA if magicka >= stamina else ResourceType.STAMINA


def _wire_sustain_heavy_generation(page) -> None:
    """Make normal V2 sustain use the already-built recovery-heavy fixed point.

    This is deliberately independent of the hidden encounter-aware Advanced mode.
    Required-effect Heavy Attacks remain available even when reserve stabilization is
    disabled; ``Use when needed`` and ``Prefer safe windows`` additionally allow
    resource pressure to schedule legal fully charged Heavy Attacks.
    """
    generation = page.rotation_generation
    if bool(getattr(generation, "_rotation_v2_sustain_heavy_installed", False)):
        return

    original_generate_with_evidence = generation.generate_with_evidence
    static_service = RotationStaticBuildContextService()
    heavy_service = RotationHeavySustainProjectionService(
        progression_adapter=static_service.progression_adapter
    )
    character_adapter = SavedBuildCharacterAdapter(get_data_dir() / "eso.db")

    def generate_with_sustain_heavies(_service, *, build, request):
        page._rotation_v2_last_recovery_projection = None
        behavior = str(page.rotation_heavy_behavior_combo.currentText() or "").strip()
        if behavior not in {"Use when needed", "Prefer safe windows"}:
            return original_generate_with_evidence(build=build, request=request)

        front_skills = tuple(getattr(build, "FrontBarSkills", ()) or ())[:5]
        initial_bar = "front" if any(str(skill or "").strip() for skill in front_skills) else "back"
        static_context = static_service.resolve(build)
        if not static_context.contexts:
            raise ValueError(
                "sustain Heavy Attacks require a resolved canonical static build context"
            )

        resource = _primary_resource(page, static_context, initial_bar)
        maximum_amount = static_context.maximum_amount_for(initial_bar, resource)
        trigger_fraction = float(page.rotation_minimum_reserve_spin.value()) / 100.0
        if maximum_amount <= 0:
            raise ValueError("sustain Heavy Attacks require a positive resource maximum")

        adaptation = character_adapter.adapt(
            build,
            character_id=str(
                getattr(static_context.progression, "character_id", "") or ""
            ).strip() or None,
        )
        if adaptation.build is None:
            detail = "; ".join(adaptation.unresolved) or "canonical build adaptation failed"
            raise ValueError("sustain Heavy Attacks unavailable: " + detail)
        character_build = adaptation.build

        generated_results: list[RotationGenerationResult] = []

        def generate(pressure_resolver):
            iteration_request = replace(
                request,
                stabilize_recovery_heavies=False,
                recovery_pressure_resolver=pressure_resolver,
            )
            result = original_generate_with_evidence(
                build=build,
                request=iteration_request,
            )
            generated_results.append(result)
            return result.plan

        def restoration_factory(plan):
            completion = heavy_service.completion_evidence_from_verified_reservations(plan)
            return heavy_service.restoration_resolver_for_plan(
                character_build=character_build,
                sustain_build=build,
                plan=plan,
                resource=resource,
                initial_bar=initial_bar,
                completion_evidence=completion,
            )

        stabilization = generation.recovery_stabilization.stabilize(
            build=build,
            generate=generate,
            resource=resource,
            maximum_amount=maximum_amount,
            trigger_fraction=trigger_fraction,
            restoration_resolver_factory=restoration_factory,
            max_iterations=6,
            calculation_context=static_context.context_for(initial_bar),
            maximum_event_resolver=(
                lambda plan, tracked_resource: static_context.maximum_events_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
            displayed_recovery_resolver_factory=(
                lambda plan, tracked_resource: static_context.displayed_recovery_resolver_for(
                    plan,
                    tracked_resource,
                    initial_bar=initial_bar,
                )
            ),
        )
        if not generated_results:
            raise RuntimeError("sustain Heavy Attack stabilization produced no generation pass")

        final_generated = generated_results[-1]
        page._rotation_v2_last_recovery_projection = stabilization.replay.final_projection
        page._rotation_v2_last_recovery_resource = resource
        return RotationGenerationResult(
            plan=stabilization.plan,
            duration_evidence=final_generated.duration_evidence,
            ultimate_projection=final_generated.ultimate_projection,
            recovery_stabilization=stabilization,
        )

    generation.generate_with_evidence = MethodType(generate_with_sustain_heavies, generation)
    generation._rotation_v2_sustain_heavy_installed = True


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

        replay_projection = getattr(page, "_rotation_v2_last_recovery_projection", None)
        replay_resource = getattr(page, "_rotation_v2_last_recovery_resource", None)
        requested_resource = kwargs.get("resource")
        if replay_projection is not None and (
            requested_resource is None or requested_resource is replay_resource
        ):
            return replay_projection
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
    _move_context_to_top_card(page)
    _install_effective_boss_build_scope(page)
    _finish_rotation_style(page)
    _finish_rules_surface(page)
    _wire_light_attack_profile(page)
    _wire_sustain_heavy_generation(page)
    _wire_resource_selection(page)
    _finish_results_card(page)
    _finish_pressure_card(page)
    _finish_compare_table(page)

    page.rotation_la_reliability_combo.setToolTip(
        "Reliable / Usually / Inconsistent currently permit Light Attack weaving; "
        "Do not rely on it removes Light Attacks from the generated baseline rotation."
    )
    page.rotation_minimum_reserve_spin.setToolTip(
        "Normal Rotation Builder sustain target. Use when needed / Prefer safe windows "
        "allows the canonical recovery-heavy fixed point to add legal Heavy Attacks."
    )
    page._rotation_builder_v2_finish_installed = True


__all__ = ["install_rotation_builder_v2_finish"]
