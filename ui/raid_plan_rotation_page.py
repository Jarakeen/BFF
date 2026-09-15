from __future__ import annotations

"""Raid Plan workspace with explicit selected-chair handoff to Rotation."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.raid_plan_coverage_page import RaidPlanCoveragePage
from ui.raid_plan_page import RAID_PLAN_SEATS, _slug


class RaidPlanRotationPage(RaidPlanCoveragePage):
    """Coverage-aware Raid Plan page that can open one exact chair in Rotation."""

    rotationRequested = Signal(object, str)

    def _build_ui(self) -> None:
        super()._build_ui()

        card = FoundryCard("Rotation / Execution", "compass")
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        label = QLabel("CHAIR")
        label.setProperty("sidebarHeading", True)
        row.addWidget(label)

        self.rotation_seat_combo = QComboBox()
        self.rotation_seat_combo.setMinimumWidth(190)
        for seat in RAID_PLAN_SEATS:
            self.rotation_seat_combo.addItem(seat, _slug(seat))
        row.addWidget(self.rotation_seat_combo, 1)

        self.open_rotation_button = FoundryButton(
            "Open Rotation",
            role=ButtonRole.PRIMARY,
            compact=True,
        )
        self.open_rotation_button.setToolTip(
            "Open Rotation with this Raid Plan chair's exact selected saved build. "
            "Encounter and execution policy remain owned by Rotation."
        )
        self.open_rotation_button.clicked.connect(self._request_rotation)
        row.addWidget(self.open_rotation_button)

        card.addWidget(row_widget)
        card.addWidget(
            QLabel(
                "Choose a chair after its saved build is selected. Rotation will use that exact build and "
                "the Raid Plan's assignment/trigger context; choose the encounter inside Rotation."
            )
        )
        self.workspace_layout.addWidget(card)

    def _request_rotation(self) -> None:
        try:
            plan = self.current_plan()
        except Exception as exc:
            self.status.error(f"Could not assemble Raid Plan for Rotation: {exc}")
            return

        seat_id = str(self.rotation_seat_combo.currentData() or "").strip()
        if not seat_id:
            self.status.warning("Choose a Raid Plan chair before opening Rotation.")
            return
        member = plan.member(seat_id)
        if member is None:
            self.status.warning("Name a player in that chair before opening Rotation.")
            return
        if not member.selected_build_name:
            self.status.warning(
                f"Select a saved build for {member.gamertag} before opening Rotation."
            )
            return
        self.rotationRequested.emit(plan, seat_id)


__all__ = ["RaidPlanRotationPage"]
