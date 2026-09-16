from __future__ import annotations

"""City After Midnight assignment surface over plan-owned RaidPlan assignments."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard
from ui.raid_plan_assignment_page import RaidPlanAssignmentPage
from ui.raid_plan_page import RAID_PLAN_SEATS, _slug


def _clean(value: object) -> str:
    return str(value or "").strip()


class CityRaidAssignmentsPage(RaidPlanAssignmentPage):
    """Mockup-shaped assignment workspace with the canonical RaidPlan editor underneath."""

    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._compose_city_workspace()
        self._refresh_city_assignment_rows()

    def _compose_city_workspace(self) -> None:
        self.header.title.setText("Assignments")
        self.header.subtitle.setText("Turn good intentions into clear jobs.")
        self.header.department.setText("RAID • ASSIGNMENTS")

        # Rehome the inherited plan/setup controls. They remain reachable as the Plan Setup
        # view but do not dominate the assignment page.
        legacy = QWidget()
        legacy_layout = QVBoxLayout(legacy)
        legacy_layout.setContentsMargins(0, 0, 0, 0)
        legacy_layout.setSpacing(8)
        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            if item.widget() is not None:
                legacy_layout.addWidget(item.widget())
            elif item.layout() is not None:
                legacy_layout.addLayout(item.layout())
        self.plan_setup_surface = legacy
        legacy.hide()

        action_row = QHBoxLayout()
        self.effective_button = QPushButton("Effective View")
        self.effective_button.setProperty("primary", True)
        action_row.addWidget(self.effective_button)
        self.plan_setup_button = QPushButton("Plan Setup")
        self.plan_setup_button.clicked.connect(self._toggle_plan_setup)
        action_row.addWidget(self.plan_setup_button)
        action_row.addStretch(1)
        save = QPushButton("Save Assignments")
        save.setProperty("primary", True)
        save.clicked.connect(self.save_current_plan)
        action_row.addWidget(save)
        self.workspace_layout.addLayout(action_row)

        body = QHBoxLayout()
        views = FoundryCard("Assignment Views", "checklist")
        for title, subtitle in (
            ("Effective View", "Current plan assignments"),
            ("Plan Assignments", "Edit this Raid Plan"),
            ("Supports", "Review support responsibilities"),
            ("Mechanics", "Review mechanic ownership"),
            ("Roles", "Group by raid role"),
        ):
            button = QPushButton(f"{title}\n{subtitle}")
            if title == "Roles":
                button.clicked.connect(self._toggle_plan_setup)
            views.addWidget(button)
        note = QLabel("Clear jobs create calm groups. Vague work stays visible as a gap.")
        note.setWordWrap(True)
        note.setProperty("muted", True)
        views.addWidget(note)
        body.addWidget(views, 2)

        table_card = FoundryCard("Team Assignments", "group")
        # Keep the canonical editable assignment columns in place and append read-only
        # context columns rather than creating a competing assignment model.
        self.assignment_table.setColumnCount(9)
        self.assignment_table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Primary Assignment", "Secondary Assignment", "Character", "Role", "Gear Needed", "Notes", "Source")
        )
        self.assignment_table.setSelectionBehavior(self.assignment_table.SelectionBehavior.SelectRows)
        self.assignment_table.itemSelectionChanged.connect(self._refresh_selected_spot)
        table_card.addWidget(self.assignment_table)
        body.addWidget(table_card, 7)

        detail = FoundryCard("Selected Spot", "feather")
        self.selected_spot_label = QLabel("Select a spot to review its plan-owned duties.")
        self.selected_spot_label.setWordWrap(True)
        detail.addWidget(self.selected_spot_label)
        open_build = QPushButton("Open Build")
        open_build.clicked.connect(lambda: self.pageRequested.emit("console:2"))
        detail.addWidget(open_build)
        open_rotation = QPushButton("Open Rotation")
        open_rotation.clicked.connect(lambda: self.pageRequested.emit("rotations"))
        detail.addWidget(open_rotation)
        edit_roles = QPushButton("Edit Roles / Spots")
        edit_roles.clicked.connect(self._toggle_plan_setup)
        detail.addWidget(edit_roles)
        body.addWidget(detail, 3)
        self.workspace_layout.addLayout(body)

        bottom = QHBoxLayout()
        summary = FoundryCard("Assignment Summary", "group")
        self.assignment_summary_label = QLabel("")
        self.assignment_summary_label.setWordWrap(True)
        summary.addWidget(self.assignment_summary_label)
        bottom.addWidget(summary, 1)
        coverage = FoundryCard("Mechanic Coverage", "shield")
        coverage_text = QLabel("Coverage evidence remains owned by Coverage. Open it for provider/recipient truth.")
        coverage_text.setWordWrap(True)
        coverage.addWidget(coverage_text)
        open_coverage = QPushButton("Open Coverage")
        open_coverage.clicked.connect(lambda: self.pageRequested.emit("console:7"))
        coverage.addWidget(open_coverage)
        bottom.addWidget(coverage, 1)
        self.workspace_layout.addLayout(bottom)
        self.workspace_layout.addWidget(legacy)

    def _toggle_plan_setup(self) -> None:
        visible = not self.plan_setup_surface.isVisible()
        self.plan_setup_surface.setVisible(visible)
        self.plan_setup_button.setText("Hide Plan Setup" if visible else "Plan Setup")

    def _refresh_city_assignment_rows(self) -> None:
        if not hasattr(self, "assignment_table"):
            return
        plan = None
        try:
            plan = self.current_plan()
        except Exception:
            pass
        members = {member.seat_id.casefold(): member for member in plan.members} if plan is not None else {}
        assigned = 0
        for row, spot in enumerate(RAID_PLAN_SEATS):
            member = members.get(_slug(spot).casefold())
            context = (
                _clean(member.character_name) if member else "",
                _clean(member.role) if member else "",
                "—",
                _clean(member.notes) if member else "",
                "Raid Plan" if member else "Unassigned",
            )
            for offset, value in enumerate(context, start=4):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.assignment_table.setItem(row, offset, item)
            if member and (member.primary_assignment or member.secondary_assignment):
                assigned += 1
        self.assignment_summary_label.setText(
            f"{assigned} / {len(RAID_PLAN_SEATS)} spots have explicit plan assignments.\n"
            "Primary and Secondary fields are durable RaidPlan intent. Gear-needed remains unclaimed here rather than being invented."
        )
        self._refresh_selected_spot()

    def _refresh_selected_spot(self) -> None:
        row = self.assignment_table.currentRow()
        if row < 0:
            self.selected_spot_label.setText("Select a spot to review its plan-owned duties.")
            return
        spot = RAID_PLAN_SEATS[row]
        try:
            plan = self.current_plan()
            member = plan.member(_slug(spot))
        except Exception:
            member = None
        if member is None:
            self.selected_spot_label.setText(f"{spot}\nNo player assigned to this spot yet.")
            return
        self.selected_spot_label.setText(
            f"{spot}\n"
            f"Player: {member.gamertag}\n"
            f"Character: {_clean(member.character_name) or 'Not selected'}\n"
            f"Role: {_clean(member.role) or 'Not selected'}\n"
            f"Primary Assignment: {_clean(member.primary_assignment) or 'Not set'}\n"
            f"Secondary Assignment: {_clean(member.secondary_assignment) or 'Not set'}\n"
            f"Linked Build: {_clean(member.selected_build_name) or 'Not selected'}\n"
            f"Notes: {_clean(member.notes) or 'None'}"
        )

    def apply_plan(self, plan) -> None:
        super().apply_plan(plan)
        if hasattr(self, "assignment_summary_label"):
            self._refresh_city_assignment_rows()

    def save_current_plan(self) -> None:
        super().save_current_plan()
        if hasattr(self, "assignment_summary_label"):
            self._refresh_city_assignment_rows()


__all__ = ["CityRaidAssignmentsPage"]
