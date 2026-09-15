from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.raid_plan_rotation_page import RaidPlanRotationPage


class RaidPlanAdviserPage(RaidPlanRotationPage):
    """Raid Plan workspace whose existing Optimizer action hands off the current plan."""

    adviserRequested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._install_adviser_action()
        self._rehome_header_plan_actions()

    def _install_adviser_action(self) -> None:
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

    def _rehome_header_plan_actions(self) -> None:
        """Keep the header for context; put plan actions in a normal workspace row."""
        saved_combo = getattr(self, "saved_plan_combo", None)
        coverage_button = getattr(self, "check_plan_coverage_button", None)
        if saved_combo is None or coverage_button is None:
            return

        saved_host = saved_combo.parentWidget()
        if saved_host is not None:
            self.header.context_layout.removeWidget(saved_host)
            saved_combo.setParent(None)
            saved_host.hide()

        self.header.context_layout.removeWidget(coverage_button)
        coverage_button.hide()

        card = FoundryCard("Plan Controls", "checklist")
        row_host = QWidget()
        row = QHBoxLayout(row_host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        saved_label = QLabel("SAVED PLAN")
        saved_label.setProperty("sidebarHeading", True)
        row.addWidget(saved_label)

        saved_combo.setMinimumWidth(260)
        row.addWidget(saved_combo, 1)

        self.load_plan_button = QPushButton("Load")
        self.load_plan_button.clicked.connect(self.load_selected_plan)
        row.addWidget(self.load_plan_button)

        self.save_plan_button = QPushButton("Save")
        self.save_plan_button.clicked.connect(self.save_current_plan)
        row.addWidget(self.save_plan_button)

        self.delete_plan_button = QPushButton("Delete")
        self.delete_plan_button.clicked.connect(self.delete_selected_plan)
        row.addWidget(self.delete_plan_button)

        row.addStretch(1)

        self.check_plan_coverage_button = FoundryButton(
            "Check Plan Coverage",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.check_plan_coverage_button.setToolTip(
            "Audit exactly this Raid Plan's selected saved builds and explicit Primary/Secondary provider labels."
        )
        self.check_plan_coverage_button.clicked.connect(self._request_plan_coverage)
        row.addWidget(self.check_plan_coverage_button)

        card.addWidget(row_host)
        self.plan_controls_card = card
        self.workspace_layout.insertWidget(0, card)


__all__ = ["RaidPlanAdviserPage"]
