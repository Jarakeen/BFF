from __future__ import annotations

from PySide6.QtCore import Signal

from ui.components.foundry_button import FoundryButton
from ui.raid_plan_rotation_page import RaidPlanRotationPage


class RaidPlanAdviserPage(RaidPlanRotationPage):
    """Raid Plan workspace whose existing Optimizer action hands off the current plan."""

    adviserRequested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        for button in self.findChildren(FoundryButton):
            if button.text().strip() != "Open Optimizer":
                continue
            button.setText("Open Adviser")
            button.setToolTip(
                "Review this exact Raid Plan in Optimizer Adviser. Recommendations are read-only and never rewrite the plan."
            )
            try:
                button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            button.clicked.connect(lambda *_: self.adviserRequested.emit(self.current_plan()))
            self.adviser_button = button
            break


__all__ = ["RaidPlanAdviserPage"]
