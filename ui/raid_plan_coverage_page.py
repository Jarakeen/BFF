from __future__ import annotations

"""Raid Plan workspace with Coverage available as an independent destination page."""

from PySide6.QtCore import Signal

from ui.raid_plan_assignment_page import RaidPlanAssignmentPage


class RaidPlanCoveragePage(RaidPlanAssignmentPage):
    """Assignment-aware Raid Plan page.

    Coverage selection is owned by the Coverage page itself. This class keeps the
    compatibility signal for older callers but does not add a special handoff button.
    """

    coverageRequested = Signal(object)

    def _request_plan_coverage(self) -> None:
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.status.error(f"Could not assemble Raid Plan for Coverage: {exc}")
            return
        self.coverageRequested.emit(plan)


__all__ = ["RaidPlanCoveragePage"]
