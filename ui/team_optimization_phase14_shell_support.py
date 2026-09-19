from __future__ import annotations

"""Phase 14 Recommendation Workbench for one exact saved Raid Plan.

The legacy Optimization editor remains intact behind this presentation layer for
older handoffs.  The visible Phase 14 surface is deliberately plan-scoped and
read-only: it renders canonical adviser findings, lets the raid lead select items
for review, and never applies or fabricates a build/team change.
"""

from time import perf_counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models.raid_plan import RaidPlan
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_SET_SCOPE = None

_CANONICAL_SEATS = (
    ("tank-1", "Tank 1", ("tank-1", "main-tank")),
    ("tank-2", "Tank 2", ("tank-2", "off-tank")),
    ("healer-1", "Healer 1", ("healer-1",)),
    ("healer-2", "Healer 2", ("healer-2",)),
    ("dd-1", "DD 1", ("dd-1",)),
    ("dd-2", "DD 2", ("dd-2",)),
    ("dd-3", "DD 3", ("dd-3",)),
    ("dd-4", "DD 4", ("dd-4",)),
    ("dd-5", "DD 5", ("dd-5",)),
    ("dd-6", "DD 6", ("dd-6",)),
    ("dd-7", "DD 7", ("dd-7",)),
    ("dd-8", "DD 8", ("dd-8",)),
)


def _seat_key(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("'", "").split())


def _context_field(page, title: str, widget: QWidget) -> QWidget:
    return page._context_field(title, widget)


def _hide_legacy_surface(page) -> None:
    for name in (
        "mode_tabs",
        "available_card",
        "team_tabs",
        "analysis_card",
        "support_card",
        "risks_card",
        "change_card",
        "gear_card",
        "skill_card",
        "notes_card",
        "raid_plan_adviser_card",
    ):
        widget = getattr(page, name, None)
        if widget is not None:
            widget.hide()

    for name in (
        "goal_combo",
        "difficulty_combo",
        "group_size_combo",
        "team_source_combo",
    ):
        widget = getattr(page, name, None)
        if widget is not None and widget.parentWidget() is not None:
            widget.parentWidget().hide()

    constraint_anchor = getattr(page, "required_slot_combo", None)
    ancestor = constraint_anchor.parentWidget() if constraint_anchor is not None else None
    while ancestor is not None and not isinstance(ancestor, FoundryCard):
        ancestor = ancestor.parentWidget()
    if ancestor is not None:
        ancestor.hide()


def _configure_table(table: QTableWidget) -> None:
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setHighlightSections(False)


def _build_header_context(page) -> None:
    page.optimizer_plan_combo = QComboBox()
    page.optimizer_plan_combo.addItem("Open from Raid Plan…", None)
    page.optimizer_plan_combo.setEnabled(False)
    page.header.add_context_widget(
        _context_field(page, "RAID PLAN", page.optimizer_plan_combo)
    )

    page.optimizer_encounter_combo = QComboBox()
    page.optimizer_encounter_combo.addItem("Plan encounter", None)
    page.optimizer_encounter_combo.setEnabled(False)
    page.header.add_context_widget(
        _context_field(page, "ENCOUNTER", page.optimizer_encounter_combo)
    )

    page.optimizer_difficulty_combo = QComboBox()
    page.optimizer_difficulty_combo.addItem("Plan difficulty", None)
    page.optimizer_difficulty_combo.setEnabled(False)
    page.header.add_context_widget(
        _context_field(page, "DIFFICULTY", page.optimizer_difficulty_combo)
    )

    page.optimizer_posture_combo = QComboBox()
    page.optimizer_posture_combo.addItems(("Safe Prog", "Balanced", "Max Output"))
    page.optimizer_posture_combo.setCurrentText("Balanced")
    page.optimizer_posture_combo.setToolTip(
        "Changes review ordering only. It does not invent damage, uptime, or survival estimates."
    )
    page.header.add_context_widget(
        _context_field(page, "REVIEW POSTURE", page.optimizer_posture_combo)
    )


def _build_scope_message(page) -> None:
    message = QLabel(
        "No Raid Plan is loaded. Go to Raid Plans, select and Load the saved plan, "
        "then choose Open Adviser. An empty or partial team can still be opened; "
        "Optimization will flag unfilled chairs."
    )
    message.setWordWrap(True)
    message.setProperty("fieldNote", True)
    message.setToolTip(
        "The My Plans list does not automatically hand a plan to Team Optimization."
    )
    page.optimizer_scope_message = message
    page.layout.addWidget(message)


def _build_team_snapshot(page) -> None:
    card = FoundryCard("Current Team (Read-Only)", "users")
    card.set_badge("0/12")

    protected = QToolButton()
    protected.setText("Protected Choices · 0")
    protected.setCheckable(True)
    protected.setToolTip(
        "Show Comp Maker choices that Optimization must preserve unless the raid lead explicitly unlocks them."
    )
    card.set_header_action(protected)

    details = QLabel("No protected Comp Maker choices are recorded on this plan.")
    details.setWordWrap(True)
    details.hide()
    protected.toggled.connect(details.setVisible)
    card.addWidget(details)

    table = QTableWidget(1, len(_CANONICAL_SEATS))
    table.setHorizontalHeaderLabels(tuple(label for _key, label, _aliases in _CANONICAL_SEATS))
    _configure_table(table)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setDefaultSectionSize(68)
    table.setMinimumHeight(104)
    table.setMaximumHeight(118)
    card.addWidget(table)

    page.optimizer_team_card = card
    page.optimizer_team_table = table
    page.optimizer_protected_button = protected
    page.optimizer_protected_details = details
    page.layout.addWidget(card)


def _build_recommendation_workspace(page) -> None:
    main = QHBoxLayout()
    main.setSpacing(10)

    recommendations = FoundryCard("Recommended Improvements", "optimization")
    introduction = QLabel(
        "Ranked review items from the selected Raid Plan and canonical evidence. "
        "Select only the changes you want to inspect; nothing is applied automatically."
    )
    introduction.setWordWrap(True)
    recommendations.addWidget(introduction)

    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(
        ("SELECT", "CHANGE", "EXPECTED OUTCOME", "TRADEOFF", "CONFIDENCE", "AFFECTED")
    )
    _configure_table(table)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    table.setMinimumHeight(330)
    recommendations.addWidget(table)
    main.addWidget(recommendations, 7)

    health = FoundryCard("Projected Team Health", "coverage")
    health_intro = QLabel(
        "Current evidence compared with the state required before a proposed change can be trusted."
    )
    health_intro.setWordWrap(True)
    health.addWidget(health_intro)

    health_table = QTableWidget(5, 3)
    health_table.setHorizontalHeaderLabels(("METRIC", "CURRENT", "PROJECTED / BOUNDARY"))
    _configure_table(health_table)
    health_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    health_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    health_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    health.addWidget(health_table)

    why = QLabel(
        "Why this matters\nFoundry separates provider capability, assignment intent, and runtime uptime. "
        "A promising swap is not an improvement until all three remain valid."
    )
    why.setWordWrap(True)
    why.setProperty("fieldNote", True)
    health.addWidget(why)
    main.addWidget(health, 3)

    page.optimizer_recommendation_card = recommendations
    page.optimizer_recommendation_table = table
    page.optimizer_health_card = health
    page.optimizer_health_table = health_table
    page.layout.addLayout(main, 1)


def _build_action_bar(page) -> None:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(10)

    selected = QLabel("0 changes selected")
    selected.setProperty("statusText", True)
    layout.addWidget(selected)

    warning = QLabel(
        "Review only. Existing builds and the saved Raid Plan will not be overwritten."
    )
    warning.setWordWrap(True)
    layout.addWidget(warning, 1)

    save_scenario = QPushButton("Save Scenario")
    save_scenario.setEnabled(False)
    save_scenario.setToolTip(
        "Scenario persistence will be enabled only after a canonical proposal model is connected."
    )
    layout.addWidget(save_scenario)

    review = QPushButton("Review Selected Changes")
    review.setProperty("primary", True)
    review.setEnabled(False)
    layout.addWidget(review)

    page.optimizer_selected_label = selected
    page.optimizer_save_scenario_button = save_scenario
    page.optimizer_review_button = review
    page.optimizer_action_bar = host
    page.layout.addWidget(host)


def _member_for_aliases(raid_plan: RaidPlan, aliases: tuple[str, ...]):
    wanted = {_seat_key(value) for value in aliases}
    for member in raid_plan.members:
        if _seat_key(member.seat_id) in wanted:
            return member
    return None


def _render_team(page, raid_plan: RaidPlan) -> int:
    named = 0
    protected_rows: list[str] = []
    for column, (_seat_id, display, aliases) in enumerate(_CANONICAL_SEATS):
        member = _member_for_aliases(raid_plan, aliases)
        if member is None:
            value = "Open chair\n—"
        else:
            player = str(member.gamertag or member.character_name or "Open chair").strip()
            detail = str(member.eso_class or member.selected_build_name or "—").strip()
            value = f"{player}\n{detail}"
            if player != "Open chair":
                named += 1
            for field in member.comp_locked_fields:
                protected_rows.append(f"{display}: {field.replace('_', ' ').title()}")
        item = QTableWidgetItem(value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setToolTip(f"{display}\n{value}")
        page.optimizer_team_table.setItem(0, column, item)

    page.optimizer_team_card.set_badge(f"{named}/12")
    page.optimizer_protected_button.setText(
        f"Protected Choices · {len(protected_rows)}"
    )
    page.optimizer_protected_details.setText(
        "\n".join(protected_rows)
        if protected_rows
        else "No protected Comp Maker choices are recorded on this plan."
    )
    return named


def _render_scope_message(page, raid_plan: RaidPlan, named_chairs: int) -> None:
    if named_chairs <= 0:
        page.optimizer_scope_message.setText(
            f"Raid Plan loaded: {raid_plan.name}. Its team has no filled chairs yet. "
            "Optimization can report plan-level gaps, but player and build recommendations "
            "need chairs filled in Raid Plan or Comp Maker and then saved."
        )
        page.optimizer_scope_message.show()
        return
    if named_chairs < len(_CANONICAL_SEATS):
        page.optimizer_scope_message.setText(
            f"Raid Plan loaded with {named_chairs}/12 filled chairs. Optimization will "
            "review those chairs now and report the remaining open chairs as blockers."
        )
        page.optimizer_scope_message.show()
        return
    page.optimizer_scope_message.hide()


def _tradeoff_for(finding) -> str:
    return {
        "blocker": "Resolve before optimization",
        "coverage_gap": "Requires an exact provider and compatible build",
        "conditional": "Execution and uptime must still be proven",
        "redundancy": "Overlap may be intentional for phase coverage",
        "data_gap": "Evidence work; not a player change",
    }.get(finding.category, "Review evidence")


def _ordered_findings(page, review):
    posture = page.optimizer_posture_combo.currentText()
    category_rank = {
        "Safe Prog": {"blocker": 0, "conditional": 1, "coverage_gap": 2, "redundancy": 3, "data_gap": 4},
        "Balanced": {"blocker": 0, "coverage_gap": 1, "conditional": 2, "redundancy": 3, "data_gap": 4},
        "Max Output": {"blocker": 0, "redundancy": 1, "coverage_gap": 2, "conditional": 3, "data_gap": 4},
    }[posture]
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    return tuple(
        sorted(
            review.findings,
            key=lambda finding: (
                category_rank[finding.category],
                priority_rank[finding.priority],
                finding.subject.casefold(),
                finding.evidence.casefold(),
            ),
        )
    )


def _render_recommendations(page, review) -> None:
    table = page.optimizer_recommendation_table
    findings = _ordered_findings(page, review)
    page._optimizer_rendered_findings = findings
    page._optimizer_table_guard = True
    try:
        table.clearSpans()
        table.clearContents()
        table.setRowCount(max(1, len(findings)))
        if not findings:
            item = QTableWidgetItem("No static plan changes are suggested by current evidence.")
            table.setItem(0, 1, item)
            table.setSpan(0, 1, 1, 5)
        else:
            for row, finding in enumerate(findings):
                selectable = finding.category in {"coverage_gap", "conditional", "redundancy"}
                select_item = QTableWidgetItem("")
                if selectable:
                    select_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    select_item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    select_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    select_item.setToolTip(
                        "This row is a blocker or evidence task, not an optimization change."
                    )
                select_item.setData(Qt.ItemDataRole.UserRole, row)
                table.setItem(row, 0, select_item)

                affected = ", ".join(finding.affected_seats) or "Raid Plan"
                values = (
                    f"{finding.subject}\n{finding.current_state}",
                    finding.proposed_state,
                    _tradeoff_for(finding),
                    finding.confidence.title(),
                    affected,
                )
                for column, value in enumerate(values, start=1):
                    item = QTableWidgetItem(str(value))
                    item.setToolTip(
                        f"Recommendation: {finding.recommendation}\n\nEvidence: {finding.evidence}"
                    )
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
                    )
                    table.setItem(row, column, item)
    finally:
        page._optimizer_table_guard = False
    _update_selected_count(page)


def _render_health(page, review) -> None:
    rows = (
        ("Coverage", review.coverage_summary, "Selected changes require provider re-evaluation"),
        (
            "Build Resolution",
            f"{review.resolved_build_count}/{review.named_member_count} exact builds",
            "Every affected chair must resolve to one canonical build",
        ),
        ("Survival", "Not evaluated", "No claim without encounter/runtime evidence"),
        ("Sustain", "Not evaluated", "No claim without rotation-resource evidence"),
        ("Raid Damage", "Not evaluated", "No synthetic percentage or DPS estimate"),
    )
    table = page.optimizer_health_table
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setToolTip(value)
            table.setItem(row, column, item)


def _selected_findings(page):
    selected = []
    table = page.optimizer_recommendation_table
    findings = tuple(getattr(page, "_optimizer_rendered_findings", ()) or ())
    for row in range(min(table.rowCount(), len(findings))):
        item = table.item(row, 0)
        if item is not None and item.checkState() == Qt.CheckState.Checked:
            selected.append(findings[row])
    return tuple(selected)


def _update_selected_count(page, *_args) -> None:
    if getattr(page, "_optimizer_table_guard", False):
        return
    selected = _selected_findings(page)
    page.optimizer_selected_label.setText(f"{len(selected)} changes selected")
    page.optimizer_review_button.setEnabled(bool(selected))


def _review_selected(page) -> None:
    selected = _selected_findings(page)
    if not selected:
        return
    lines = []
    for index, finding in enumerate(selected, start=1):
        lines.append(
            f"{index}. {finding.subject}\n"
            f"   Current: {finding.current_state}\n"
            f"   Review: {finding.proposed_state}\n"
            f"   Confidence: {finding.confidence.title()}\n"
            f"   Evidence: {finding.evidence}"
        )
    QMessageBox.information(
        page,
        "Selected Optimization Reviews",
        "\n\n".join(lines)
        + "\n\nNo build or Raid Plan value has been changed.",
    )


def _render_plan_context(page, raid_plan: RaidPlan) -> None:
    page.optimizer_plan_combo.clear()
    page.optimizer_plan_combo.addItem(raid_plan.name, raid_plan.plan_id)
    page.optimizer_encounter_combo.clear()
    page.optimizer_encounter_combo.addItem(raid_plan.trial_id, raid_plan.trial_id)
    page.optimizer_difficulty_combo.clear()
    page.optimizer_difficulty_combo.addItem(
        str(raid_plan.difficulty or "Not recorded"), raid_plan.difficulty
    )


def _render_workbench(page, raid_plan: RaidPlan, review) -> None:
    _hide_legacy_surface(page)
    _render_plan_context(page, raid_plan)
    named_chairs = _render_team(page, raid_plan)
    _render_scope_message(page, raid_plan, named_chairs)
    _render_recommendations(page, review)
    _render_health(page, review)
    page.optimizer_recommendation_card.set_badge(
        f"{review.actionable_count} ACTIONABLE"
    )
    page.status.info(
        f"Team Optimization • {review.plan_name} • {review.coverage_summary} • review only"
    )


def _refresh_posture(page) -> None:
    review = getattr(page, "_raid_plan_adviser_review", None)
    if review is not None:
        _render_recommendations(page, review)


def _init_with_phase14_workbench(self, parent=None) -> None:
    """Construct only the lightweight Phase 14 plan-scoped Optimization surface."""
    started = perf_counter()
    FoundryPage.__init__(self, parent)

    self.header = FoundryHeader(
        title="Team Optimization",
        subtitle="Audit and refine one saved Raid Plan. Composition creation lives in Comp Maker.",
        department="RAID ENGINE • OPTIMIZATION",
    )
    self.set_header(self.header)

    self.workspace = QWidget()
    self.layout = QVBoxLayout(self.workspace)
    self.layout.setContentsMargins(0, 0, 0, 0)
    self.layout.setSpacing(10)
    self.add_workspace(self.workspace)

    self.status = FoundryStatusBar()
    self.set_status(self.status)

    _build_header_context(self)
    _build_scope_message(self)
    _build_team_snapshot(self)
    _build_recommendation_workspace(self)
    _build_action_bar(self)

    self._optimizer_rendered_findings = ()
    self._optimizer_table_guard = False
    self._raid_plan_adviser_scope = None
    self._raid_plan_adviser_review = None
    self._raid_plan_optimizer_adviser_service = None
    self._optimizer_saved_build_service = None
    self._optimizer_startup_profile = {
        "legacy_constructor_invoked": False,
        "build_resolution_deferred": True,
        "adviser_service_deferred": True,
        "phase14_constructor_ms": (perf_counter() - started) * 1000.0,
    }

    self.optimizer_recommendation_table.itemChanged.connect(
        lambda *_: _update_selected_count(self)
    )
    self.optimizer_posture_combo.currentTextChanged.connect(
        lambda *_: _refresh_posture(self)
    )
    self.optimizer_review_button.clicked.connect(lambda *_: _review_selected(self))
    self.status.info(
        "Open Team Optimization from a saved Raid Plan to receive evidence-backed recommendations."
    )


def _ensure_adviser_services(page) -> None:
    """Create expensive saved-build/adviser services only for an explicit Raid Plan."""
    if page._raid_plan_optimizer_adviser_service is not None:
        return

    from engine.config import get_data_dir
    from services.build_service import BuildService
    from services.raid_plan_optimizer_adviser_service import RaidPlanOptimizerAdviserService
    from services.saved_build_capability_service import SavedBuildCapabilityService

    data_dir = get_data_dir()
    builds = BuildService(data_dir / "builds.json")
    capability = SavedBuildCapabilityService(builds, data_dir / "eso.db")
    page._optimizer_saved_build_service = builds
    page._raid_plan_optimizer_adviser_service = RaidPlanOptimizerAdviserService(capability)
    page._optimizer_startup_profile["adviser_service_deferred"] = False


def _set_scope_with_phase14_workbench(self, raid_plan: RaidPlan) -> None:
    """Load one exact saved Raid Plan without constructing the legacy Optimization UI."""
    if not isinstance(raid_plan, RaidPlan):
        raise TypeError("Optimizer Adviser Raid Plan scope requires RaidPlan")

    started = perf_counter()
    _ensure_adviser_services(self)
    roster = self._optimizer_saved_build_service.load()
    saved_builds = tuple(getattr(roster, "Members", ()) or ())
    self._optimizer_startup_profile["build_resolution_deferred"] = False

    review = self._raid_plan_optimizer_adviser_service.review(
        raid_plan=raid_plan,
        saved_builds=saved_builds,
        total_chairs=len(_CANONICAL_SEATS),
    )
    self._raid_plan_adviser_scope = raid_plan
    self._raid_plan_adviser_review = review
    self._optimizer_startup_profile["last_plan_scope_ms"] = (
        perf_counter() - started
    ) * 1000.0
    _render_workbench(self, raid_plan, review)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_SET_SCOPE
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    # Keep references only for compatibility diagnostics. Normal Phase 14 startup
    # never calls either legacy implementation.
    _ORIGINAL_INIT = OptimizationPage.__init__
    _ORIGINAL_SET_SCOPE = getattr(OptimizationPage, "set_raid_plan_adviser_scope", None)
    OptimizationPage.__init__ = _init_with_phase14_workbench
    OptimizationPage.set_raid_plan_adviser_scope = _set_scope_with_phase14_workbench
    _INSTALLED = True


__all__ = ["install"]
