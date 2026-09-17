from __future__ import annotations

"""Urban Wilderness assignment surface over plan-owned RaidPlan assignments."""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFormLayout,
    QHeaderView,
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
from ui.ux_icons import set_button_icon


def _clean(value: object) -> str:
    return str(value or "").strip()


def _role_icon_name(role: str) -> str:
    """Map ESO raid-role language to a semantic Selected Spot role mark."""
    value = _clean(role).casefold()
    if "support" in value and any(token in value for token in ("dd", "dps", "damage")):
        return "support-dd"
    if "heal" in value:
        return "healer"
    if "tank" in value:
        return "tank"
    if any(token in value for token in ("dd", "dps", "damage")):
        return "dd"
    return ""


def _role_icon_pixmap(role_key: str, size: int = 28) -> QPixmap:
    """Draw a compact bronze/cyan role mark without depending on assets/icons."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if not role_key:
        return pixmap

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    bronze = QColor("#C8A46A")
    cyan = QColor("#59AEB3")
    dark = QColor("#0C171B")
    line = max(2.0, size / 11.0)
    painter.setPen(QPen(bronze, line, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    if role_key == "healer":
        painter.setBrush(cyan)
        arm = size * 0.20
        thickness = size * 0.12
        center = size / 2
        painter.drawRoundedRect(QRectF(center - thickness / 2, center - arm, thickness, arm * 2), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(center - arm, center - thickness / 2, arm * 2, thickness), 1.5, 1.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(size * 0.19, size * 0.19, size * 0.62, size * 0.62))
    elif role_key == "tank":
        path = QPainterPath()
        path.moveTo(QPointF(size * 0.50, size * 0.12))
        path.lineTo(QPointF(size * 0.78, size * 0.24))
        path.lineTo(QPointF(size * 0.72, size * 0.66))
        path.quadTo(QPointF(size * 0.62, size * 0.83), QPointF(size * 0.50, size * 0.90))
        path.quadTo(QPointF(size * 0.38, size * 0.83), QPointF(size * 0.28, size * 0.66))
        path.lineTo(QPointF(size * 0.22, size * 0.24))
        path.closeSubpath()
        painter.setBrush(dark)
        painter.drawPath(path)
        painter.setPen(QPen(cyan, line * 0.7))
        painter.drawLine(QPointF(size * 0.50, size * 0.25), QPointF(size * 0.50, size * 0.72))
    else:
        # Crossed blades read as damage; Support DD gains a cyan support spark.
        painter.drawLine(QPointF(size * 0.23, size * 0.76), QPointF(size * 0.73, size * 0.22))
        painter.drawLine(QPointF(size * 0.27, size * 0.22), QPointF(size * 0.77, size * 0.76))
        painter.drawLine(QPointF(size * 0.18, size * 0.68), QPointF(size * 0.30, size * 0.80))
        painter.drawLine(QPointF(size * 0.70, size * 0.80), QPointF(size * 0.82, size * 0.68))
        if role_key == "support-dd":
            painter.setPen(QPen(cyan, line * 0.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            center = QPointF(size * 0.76, size * 0.24)
            radius = size * 0.11
            painter.drawLine(QPointF(center.x() - radius, center.y()), QPointF(center.x() + radius, center.y()))
            painter.drawLine(QPointF(center.x(), center.y() - radius), QPointF(center.x(), center.y() + radius))

    painter.end()
    return pixmap


class CityRaidAssignmentsPage(RaidPlanAssignmentPage):
    """Readable assignment summary with detailed editing kept in the selected-spot panel."""

    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._compose_city_workspace()
        self._refresh_city_assignment_rows()

    def _compose_city_workspace(self) -> None:
        self.header.title.setText("Assignments")
        self.header.subtitle.setText("Turn good intentions into clear jobs.")
        self.header.department.setText("RAID • ASSIGNMENTS")

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
            ("Effective View", "Current plan duties"),
            ("Plan Assignments", "Edit this Raid Plan"),
            ("Supports", "Review support responsibilities"),
            ("Mechanics", "Review mechanic ownership"),
            ("Roles", "Review raid spots"),
        ):
            button = QPushButton(f"{title}\n{subtitle}")
            if title == "Roles":
                button.clicked.connect(self._toggle_plan_setup)
            views.addWidget(button)
        body.addWidget(views, 2)

        table_card = FoundryCard("Team Assignments", "group")
        self.assignment_table.setColumnCount(7)
        self.assignment_table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Main Duty", "Backup / Utility", "Gear", "Notes", "Source")
        )
        self.assignment_table.setSelectionBehavior(self.assignment_table.SelectionBehavior.SelectRows)
        self.assignment_table.itemSelectionChanged.connect(self._refresh_selected_spot)
        header = self.assignment_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.assignment_table.setColumnWidth(0, 105)
        self.assignment_table.setColumnWidth(4, 110)
        self.assignment_table.setColumnWidth(6, 100)
        table_card.addWidget(self.assignment_table)
        body.addWidget(table_card, 7)

        detail = FoundryCard("Selected Spot", "assignment")
        detail.setProperty("selectedSpotCard", True)

        self.selected_spot_title = QLabel("Select a spot")
        self.selected_spot_title.setProperty("selectedSpotTitle", True)
        self.selected_spot_title.setWordWrap(True)
        detail.addWidget(self.selected_spot_title)

        role_row = QHBoxLayout()
        role_row.setContentsMargins(0, 0, 0, 0)
        role_row.setSpacing(8)
        self.selected_spot_role_icon = QLabel()
        self.selected_spot_role_icon.setProperty("selectedSpotRoleIcon", True)
        self.selected_spot_role_icon.setFixedSize(30, 30)
        self.selected_spot_role_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_spot_role_icon.hide()
        role_row.addWidget(self.selected_spot_role_icon)
        self.selected_spot_role = QLabel("No assignment selected")
        self.selected_spot_role.setProperty("selectedSpotRole", True)
        self.selected_spot_role.setWordWrap(True)
        role_row.addWidget(self.selected_spot_role, 1)
        detail.addLayout(role_row)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 4)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)
        self.selected_player = self._selected_value_label()
        self.selected_character = self._selected_value_label()
        self.selected_primary = self._selected_value_label()
        self.selected_secondary = self._selected_value_label()
        self.selected_gear = self._selected_value_label()
        self.selected_build = self._selected_value_label()
        self.selected_notes = self._selected_value_label()
        form.addRow("Player", self.selected_player)
        form.addRow("Character", self.selected_character)
        form.addRow("Primary Assignment", self.selected_primary)
        form.addRow("Secondary Assignment", self.selected_secondary)
        form.addRow("Gear Needed", self.selected_gear)
        form.addRow("Linked Build", self.selected_build)
        form.addRow("Notes", self.selected_notes)
        detail.addLayout(form)
        detail.addStretch(1)

        open_build = QPushButton("Open Build")
        set_button_icon(open_build, "builds")
        open_build.clicked.connect(lambda: self.pageRequested.emit("console:2"))
        detail.addWidget(open_build)
        open_rotation = QPushButton("Open Rotation")
        set_button_icon(open_rotation, "rotations")
        open_rotation.clicked.connect(lambda: self.pageRequested.emit("rotations"))
        detail.addWidget(open_rotation)
        edit_roles = QPushButton("Edit Duties")
        set_button_icon(edit_roles, "pen-tool")
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
        coverage_text = QLabel("Coverage remains authoritative for provider and recipient truth.")
        coverage_text.setWordWrap(True)
        coverage.addWidget(coverage_text)
        open_coverage = QPushButton("Open Coverage")
        open_coverage.clicked.connect(lambda: self.pageRequested.emit("console:7"))
        coverage.addWidget(open_coverage)
        bottom.addWidget(coverage, 1)
        self.workspace_layout.addLayout(bottom)
        self.workspace_layout.addWidget(legacy)

    @staticmethod
    def _selected_value_label() -> QLabel:
        label = QLabel("—")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setProperty("selectedSpotValue", True)
        return label

    def _set_selected_role_icon(self, role: str) -> None:
        role_key = _role_icon_name(role)
        value = _role_icon_pixmap(role_key)
        if not role_key or value.isNull():
            self.selected_spot_role_icon.clear()
            self.selected_spot_role_icon.hide()
            return
        self.selected_spot_role_icon.setPixmap(value)
        self.selected_spot_role_icon.setProperty("semanticRoleMark", role_key)
        self.selected_spot_role_icon.setToolTip(role or "Raid role")
        self.selected_spot_role_icon.show()

    def _set_selected_spot_empty(self, title: str, message: str) -> None:
        self.selected_spot_title.setText(title)
        self.selected_spot_role.setText(message)
        self._set_selected_role_icon("")
        for label in (
            self.selected_player,
            self.selected_character,
            self.selected_primary,
            self.selected_secondary,
            self.selected_gear,
            self.selected_build,
            self.selected_notes,
        ):
            label.setText("—")

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
            f"{assigned} / {len(RAID_PLAN_SEATS)} spots have explicit duties.\n"
            "Main Duty is the canonical primary assignment. Backup / Utility is optional secondary intent."
        )
        self._refresh_selected_spot()

    def _refresh_selected_spot(self) -> None:
        row = self.assignment_table.currentRow()
        if row < 0:
            self._set_selected_spot_empty("Select a spot", "Choose a row to review its duties.")
            return
        spot = RAID_PLAN_SEATS[row]
        try:
            plan = self.current_plan()
            member = plan.member(_slug(spot))
        except Exception:
            member = None
        if member is None:
            self._set_selected_spot_empty(spot, "No player assigned to this spot yet.")
            return

        role = _clean(member.role) or "Role not selected"
        eso_class = _clean(member.eso_class)
        self.selected_spot_title.setText(spot)
        self.selected_spot_role.setText(" • ".join(value for value in (role, eso_class) if value))
        self._set_selected_role_icon(role)
        self.selected_player.setText(member.gamertag)
        self.selected_character.setText(_clean(member.character_name) or "Not selected")
        self.selected_primary.setText(_clean(member.primary_assignment) or "Not set")
        self.selected_secondary.setText(_clean(member.secondary_assignment) or "None")
        self.selected_gear.setText("Not tracked in Raid Plan")
        self.selected_build.setText(_clean(member.selected_build_name) or "Not selected")
        self.selected_notes.setText(_clean(member.notes) or "None")

    def apply_plan(self, plan) -> None:
        super().apply_plan(plan)
        if hasattr(self, "assignment_summary_label"):
            self._refresh_city_assignment_rows()

    def save_current_plan(self) -> None:
        super().save_current_plan()
        if hasattr(self, "assignment_summary_label"):
            self._refresh_city_assignment_rows()


__all__ = ["CityRaidAssignmentsPage", "_role_icon_name", "_role_icon_pixmap"]