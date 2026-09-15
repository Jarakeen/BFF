from __future__ import annotations

"""Raid Plan workspace with explicit Coverage handoff."""

from PySide6.QtCore import Signal

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.raid_plan_assignment_page import RaidPlanAssignmentPage


class RaidPlanCoveragePage(RaidPlanAssignmentPage):
    """Assignment-aware Raid Plan page that can send its exact plan to Coverage."""

    coverageRequested = Signal(object)

    def _build_ui(self) -> None:
        super()._build_ui()
        self.check_plan_coverage_button = FoundryButton(
            "Check Plan Coverage",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.check_plan_coverage_button.setToolTip(
            "Audit exactly this Raid Plan's selected saved builds and explicit Primary/Secondary provider labels."
        )
        self.check_plan_coverage_button.clicked.connect(self._request_plan_coverage)
        self.header.add_context_widget(self.check_plan_coverage_button)

    def _request_plan_coverage(self) -> None:
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.status.error(f"Could not assemble Raid Plan for Coverage: {exc}")
            return
        self.coverageRequested.emit(plan)


__all__ = ["RaidPlanCoveragePage"]
