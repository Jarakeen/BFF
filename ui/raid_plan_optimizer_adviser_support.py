from __future__ import annotations

"""Compatibility-only Raid Plan adapter for the retired Optimization editor.

The Phase 14 Recommendation Workbench owns the live set_raid_plan_adviser_scope path
directly and lazy-loads the reusable adviser service only when a plan is handed in.
"""

"""Bind an explicit RaidPlan to the existing Optimization workspace as read-only advice.

The existing Optimization page remains available for legacy/manual workflows. When opened
from Raid Plans, this adapter loads only the plan's exact saved builds and renders advisory
findings in a dedicated card. It does not apply recommendations or save team/build changes.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from engine.config import get_data_dir
from models.raid_plan import RaidPlan
from services.build_service import BuildService
from services.raid_plan_optimizer_adviser_service import RaidPlanOptimizerAdviserService
from services.raid_plan_saved_build_resolution_service import RaidPlanSavedBuildResolutionService
from services.saved_build_capability_service import SavedBuildCapabilityService
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_INIT = None


def _seat_key(value: object) -> str:
    return "-".join(str(value or "").strip().casefold().replace("'", "").split())


def _build_index(roster, build) -> int | None:
    wanted = build.to_dict()
    for index, candidate in enumerate(tuple(getattr(roster, "Members", ()) or ())):
        if candidate.to_dict() == wanted:
            return index
    return None


def _render_review(page, review) -> None:
    table = page.raid_plan_adviser_table
    summary = page.raid_plan_adviser_summary
    summary.setText(
        f"{review.plan_name} • {review.resolved_build_count}/{review.named_member_count} named chair build(s) resolved • "
        f"{review.blocker_count} blocker(s) • {review.actionable_count} actionable review item(s)\n"
        "Advisory only. No player, build, assignment, skill, gear, or Raid Plan field is changed automatically."
    )
    table.setRowCount(len(review.findings))
    for row, finding in enumerate(review.findings):
        values = (
            finding.priority.upper(),
            finding.category.replace("_", " ").title(),
            finding.subject,
            finding.recommendation,
            finding.evidence,
        )
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            if column in (0, 1, 2):
                item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            table.setItem(row, column, item)
    if not review.findings:
        table.setRowCount(1)
        table.setItem(0, 0, QTableWidgetItem("—"))
        table.setItem(0, 1, QTableWidgetItem("Review"))
        table.setItem(0, 2, QTableWidgetItem("No advisory findings"))
        table.setItem(0, 3, QTableWidgetItem("No static plan changes are suggested from current evidence."))
        table.setItem(0, 4, QTableWidgetItem("Runtime/encounter evidence may still add later advice."))


def _load_plan_into_team_editor(page, raid_plan: RaidPlan, saved_builds) -> None:
    page._populate_team_editor(page.team_table, autofill=False)
    resolver = RaidPlanSavedBuildResolutionService()
    members = {member.seat_id: member for member in raid_plan.members}
    prior_guard = getattr(page, "_team_combo_signal_guard", False)
    page._team_combo_signal_guard = True
    try:
        for row in range(page.team_table.rowCount()):
            seat_item = page.team_table.item(row, 0)
            seat_id = _seat_key(seat_item.text() if seat_item is not None else "")
            member = members.get(seat_id)
            selector = page.team_table.cellWidget(row, 1)
            if member is None or selector is None:
                continue
            result = resolver.resolve(
                raid_plan=raid_plan,
                seat_id=seat_id,
                saved_builds=saved_builds,
            )
            if not result.resolved or result.build is None:
                continue
            index = _build_index(page.roster, result.build)
            if index is None:
                continue
            combo_index = selector.findData(index)
            if combo_index >= 0:
                selector.setCurrentIndex(combo_index)
                page._team_selection_changed(page.team_table, row)
    finally:
        page._team_combo_signal_guard = prior_guard


def _set_raid_plan_adviser_scope(page, raid_plan: RaidPlan) -> None:
    if not isinstance(raid_plan, RaidPlan):
        raise TypeError("Optimizer Adviser Raid Plan scope requires RaidPlan")

    page.roster = page.build_service.load()
    saved_builds = tuple(getattr(page.roster, "Members", ()) or ())
    _load_plan_into_team_editor(page, raid_plan, saved_builds)

    review = page._raid_plan_optimizer_adviser_service.review(
        raid_plan=raid_plan,
        saved_builds=saved_builds,
        total_chairs=page.team_table.rowCount(),
    )
    page._raid_plan_adviser_scope = raid_plan
    page._raid_plan_adviser_review = review
    page.raid_plan_adviser_card.show()
    page.header.title.setText("Optimizer Adviser")
    page.header.subtitle.setText(
        "Review the selected Raid Plan and explain what to inspect without rewriting the team."
    )
    page._update_team_analysis()
    _render_review(page, review)
    page.status.info(
        f"Optimizer Adviser • {review.plan_name} • {len(review.findings)} advisory finding(s); no changes applied."
    )


def _init_with_raid_plan_adviser(self, parent=None) -> None:
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, parent)

    data_dir = get_data_dir()
    builds = BuildService(data_dir / "builds.json")
    capability = SavedBuildCapabilityService(builds, data_dir / "eso.db")
    self._raid_plan_optimizer_adviser_service = RaidPlanOptimizerAdviserService(capability)
    self._raid_plan_adviser_scope = None
    self._raid_plan_adviser_review = None

    card = FoundryCard("Optimizer Adviser", "compass")
    summary = QLabel(
        "Open this workspace from a Raid Plan to receive evidence-backed review items. "
        "The Adviser never applies changes automatically."
    )
    summary.setWordWrap(True)
    card.addWidget(summary)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("PRIORITY", "CATEGORY", "SUBJECT", "RECOMMENDATION", "EVIDENCE"))
    table.verticalHeader().setVisible(False)
    table.setMinimumHeight(260)
    table.horizontalHeader().setStretchLastSection(True)
    card.addWidget(table)
    card.hide()

    self.raid_plan_adviser_card = card
    self.raid_plan_adviser_summary = summary
    self.raid_plan_adviser_table = table
    self.layout.addWidget(card)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT
    if _INSTALLED:
        return

    from ui.optimization_page import OptimizationPage

    _ORIGINAL_INIT = OptimizationPage.__init__
    OptimizationPage.__init__ = _init_with_raid_plan_adviser
    OptimizationPage.set_raid_plan_adviser_scope = _set_raid_plan_adviser_scope
    _INSTALLED = True


__all__ = ["install"]
