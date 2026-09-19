from __future__ import annotations

"""Urban Wilderness assignment surface over plan-owned RaidPlan assignments."""

from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
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
    """Raid Plan jobs: support effects first, utility/mechanics separately."""

    pageRequested = Signal(str)

    UTILITY_CHOICES = (
        "Kite",
        "Portal",
        "Interrupts",
        "Add Control",
        "Boss Positioning",
        "Execute / Interrupts",
        "Boss Damage / Mechanic",
        "Orbs / Utility",
        "Raid Healing / Support",
        "Mechanic",
        "Utility",
        "Backup",
    )

    def __init__(self, parent=None) -> None:
        self._utility_by_seat: dict[str, tuple[str, ...]] = {}
        self._notes_by_seat: dict[str, str] = {}
        self._assignment_source_by_seat: dict[str, str] = {}
        self._selected_note_seat = ""
        self._loading_selected_notes = False
        self._loading_assignment_source = False
        super().__init__(parent)
        self._compose_city_workspace()
        self._refresh_city_assignment_rows()

    def _compose_city_workspace(self) -> None:
        self.header.title.setText("Assignments")
        self.header.subtitle.setText(
            "Assign buffs and debuffs first. Keep utility and mechanics separate."
        )
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
        action_row.addStretch(1)
        save = QPushButton("Save Assignments")
        save.setProperty("primary", True)
        save.clicked.connect(self.save_current_plan)
        action_row.addWidget(save)
        self.workspace_layout.addLayout(action_row)

        body = QHBoxLayout()

        support_card = FoundryCard("Buffs / Debuffs", "checklist")
        self.support_table = QTableWidget(len(RAID_PLAN_SEATS), 5)
        self.support_table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Buffs / Debuffs", "Gear / Build", "Source")
        )
        self.support_table.verticalHeader().setVisible(False)
        self.support_table.verticalHeader().setDefaultSectionSize(58)
        self.support_table.setMinimumHeight(430)
        self.support_table.setSelectionBehavior(
            self.support_table.SelectionBehavior.SelectRows
        )
        self.support_table.itemSelectionChanged.connect(self._refresh_selected_spot)
        support_header = self.support_table.horizontalHeader()
        support_header.setStretchLastSection(False)
        support_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        support_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        support_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        support_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        support_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        for row, spot in enumerate(RAID_PLAN_SEATS):
            spot_item = QTableWidgetItem(spot)
            spot_item.setFlags(spot_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.support_table.setItem(row, 0, spot_item)

            player_item = QTableWidgetItem("")
            player_item.setFlags(player_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.support_table.setItem(row, 1, player_item)

            support_widget = QWidget()
            support_layout = QVBoxLayout(support_widget)
            support_layout.setContentsMargins(0, 1, 0, 1)
            support_layout.setSpacing(2)
            primary = self._new_support_combo(row, 2, "Primary buff / debuff…")
            secondary = self._new_support_combo(row, 3, "Second / backup buff…")
            support_layout.addWidget(primary)
            support_layout.addWidget(secondary)
            self.support_table.setCellWidget(row, 2, support_widget)

            for column in (3, 4):
                item = QTableWidgetItem("")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.support_table.setItem(row, column, item)

        support_card.addWidget(self.support_table)
        body.addWidget(support_card, 7)

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
        self.selected_support = self._selected_value_label()
        self.selected_utility = self._selected_value_label()
        self.selected_gear = self._selected_value_label()
        self.selected_build = self._selected_value_label()
        self.selected_assignment_source = QLineEdit()
        self.selected_assignment_source.setPlaceholderText("e.g. WW, class skill, proc set…")
        self.selected_assignment_source.textChanged.connect(
            self._selected_assignment_source_changed
        )
        self.selected_notes = QPlainTextEdit()
        self.selected_notes.setPlaceholderText("Plan notes for this spot…")
        self.selected_notes.setMaximumHeight(92)
        self.selected_notes.textChanged.connect(self._selected_notes_changed)
        form.addRow("Player", self.selected_player)
        form.addRow("Character", self.selected_character)
        form.addRow("Buffs / Debuffs", self.selected_support)
        form.addRow("Utility / Mechanics", self.selected_utility)
        form.addRow("Planned Gear", self.selected_gear)
        form.addRow("Linked Build", self.selected_build)
        form.addRow("Source", self.selected_assignment_source)
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
        body.addWidget(detail, 3)
        self.workspace_layout.addLayout(body)

        utility_card = FoundryCard("Utility / Mechanics", "warning")
        self.utility_table = QTableWidget(len(RAID_PLAN_SEATS), 3)
        self.utility_table.setHorizontalHeaderLabels(("Spot", "Player", "Utility / Mechanic Job"))
        self.utility_table.verticalHeader().setVisible(False)
        self.utility_table.setMaximumHeight(310)
        self.utility_table.setSelectionBehavior(
            self.utility_table.SelectionBehavior.SelectRows
        )
        self.utility_table.itemSelectionChanged.connect(self._utility_row_selected)
        utility_header = self.utility_table.horizontalHeader()
        utility_header.setStretchLastSection(True)
        utility_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        utility_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        utility_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        for row, spot in enumerate(RAID_PLAN_SEATS):
            spot_item = QTableWidgetItem(spot)
            spot_item.setFlags(spot_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.utility_table.setItem(row, 0, spot_item)
            player_item = QTableWidgetItem("")
            player_item.setFlags(player_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.utility_table.setItem(row, 1, player_item)
            self.utility_table.setCellWidget(row, 2, self._new_utility_combo(row))
        utility_card.addWidget(self.utility_table)
        self.workspace_layout.addWidget(utility_card)

        bottom = QHBoxLayout()
        summary = FoundryCard("Assignment Summary", "group")
        self.assignment_summary_label = QLabel("")
        self.assignment_summary_label.setWordWrap(True)
        summary.addWidget(self.assignment_summary_label)
        bottom.addWidget(summary, 1)

        snapshot = FoundryCard("Plan Snapshot", "compass")
        self.plan_snapshot_label = QLabel("")
        self.plan_snapshot_label.setWordWrap(True)
        snapshot.addWidget(self.plan_snapshot_label)
        bottom.addWidget(snapshot, 1)
        self.workspace_layout.addLayout(bottom)
        self.workspace_layout.addWidget(legacy)

    def _new_support_combo(self, row: int, hidden_column: int, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.addItem("")
        combo.addItems(tuple(GROUP_COVERAGE_NAMES))
        if combo.lineEdit() is not None:
            combo.lineEdit().setClearButtonEnabled(True)
            combo.lineEdit().setPlaceholderText(placeholder)
        combo.currentTextChanged.connect(
            lambda text, row_index=row, column=hidden_column:
                self._support_assignment_changed(row_index, column, text)
        )
        return combo

    def _new_utility_combo(self, row: int) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.addItem("")
        combo.addItems(self.UTILITY_CHOICES)
        if combo.lineEdit() is not None:
            combo.lineEdit().setClearButtonEnabled(True)
            combo.lineEdit().setPlaceholderText("Type or choose utility…")
        combo.currentTextChanged.connect(
            lambda text, row_index=row: self._utility_assignment_changed(row_index, text)
        )
        return combo

    def _support_combos(self, row: int) -> tuple[QComboBox | None, QComboBox | None]:
        widget = self.support_table.cellWidget(row, 2)
        if widget is None:
            return None, None
        combos = widget.findChildren(QComboBox)
        return (
            combos[0] if len(combos) > 0 else None,
            combos[1] if len(combos) > 1 else None,
        )

    def _support_assignment_changed(self, row: int, hidden_column: int, value: str) -> None:
        self._set_assignment_text(row, hidden_column, value)
        self._refresh_assignment_summary()
        if self.support_table.currentRow() == row:
            self._refresh_selected_spot()

    def _utility_assignment_changed(self, row: int, value: str) -> None:
        seat_id = _slug(RAID_PLAN_SEATS[row])
        clean = _clean(value)
        self._utility_by_seat[seat_id] = (clean,) if clean else ()
        self._refresh_assignment_summary()
        if self.support_table.currentRow() == row:
            self._refresh_selected_spot()

    def _utility_row_selected(self) -> None:
        row = self.utility_table.currentRow()
        if row < 0:
            return
        self.support_table.blockSignals(True)
        self.support_table.selectRow(row)
        self.support_table.blockSignals(False)
        self._refresh_selected_spot()

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
        self._selected_note_seat = ""
        self.selected_spot_title.setText(title)
        self.selected_spot_role.setText(message)
        self._set_selected_role_icon("")
        for label in (
            self.selected_player,
            self.selected_character,
            self.selected_support,
            self.selected_utility,
            self.selected_gear,
            self.selected_build,
        ):
            label.setText("—")
        self._loading_assignment_source = True
        self.selected_assignment_source.clear()
        self._loading_assignment_source = False
        self._loading_selected_notes = True
        self.selected_notes.clear()
        self._loading_selected_notes = False

    def _selected_assignment_source_changed(self, value: str) -> None:
        if self._loading_assignment_source or not self._selected_note_seat:
            return
        self._assignment_source_by_seat[self._selected_note_seat] = _clean(value)
        self._refresh_city_assignment_rows()

    def _selected_notes_changed(self) -> None:
        if self._loading_selected_notes or not self._selected_note_seat:
            return
        self._notes_by_seat[self._selected_note_seat] = self.selected_notes.toPlainText()

    def _refresh_city_assignment_rows(self) -> None:
        if not hasattr(self, "support_table"):
            return
        try:
            plan = self.current_plan()
        except Exception:
            plan = None
        members = {
            member.seat_id.casefold(): member
            for member in plan.members
        } if plan is not None else {}

        for row, spot in enumerate(RAID_PLAN_SEATS):
            seat_id = _slug(spot)
            member = members.get(seat_id.casefold())
            player = _clean(member.gamertag) if member else ""
            self.support_table.item(row, 1).setText(player)
            self.utility_table.item(row, 1).setText(player)

            gear = ""
            if member is not None:
                gear = " + ".join(member.planned_gear_sets)
                if not gear:
                    gear = _clean(member.selected_build_name)
            self.support_table.item(row, 3).setText(gear or "—")
            source = ""
            if member is not None:
                source = self._assignment_source_by_seat.get(
                    seat_id.casefold(),
                    _clean(member.assignment_source),
                )
            self.support_table.item(row, 4).setText(
                source or ("Raid Plan" if member else "Unassigned")
            )

        self._refresh_assignment_summary()
        self._refresh_plan_snapshot()
        self._refresh_selected_spot()

    def _refresh_assignment_summary(self) -> None:
        if not hasattr(self, "assignment_summary_label"):
            return
        try:
            plan = self.current_plan()
        except Exception:
            return
        support_count = sum(
            bool(member.primary_assignment or member.secondary_assignment)
            for member in plan.members
        )
        utility_count = sum(bool(member.utility_assignments) for member in plan.members)
        self.assignment_summary_label.setText(
            f"{support_count} / {len(RAID_PLAN_SEATS)} spots have buff/debuff jobs.\n"
            f"{utility_count} / {len(RAID_PLAN_SEATS)} spots have utility/mechanic jobs.\n"
            "Buff/debuff ownership is kept separate from utility so Coverage can audit support cleanly."
        )

    def _refresh_plan_snapshot(self) -> None:
        if not hasattr(self, "plan_snapshot_label"):
            return
        try:
            plan = self.current_plan()
        except Exception:
            return
        named = sum(bool(_clean(member.gamertag)) for member in plan.members)
        builds = sum(
            bool(member.selected_build_name or member.planned_gear_sets)
            for member in plan.members
        )
        self.plan_snapshot_label.setText(
            f"{plan.name}\n"
            f"{plan.trial_id} • {plan.difficulty or 'Difficulty not set'}\n"
            f"{plan.team_name or 'Ad-hoc team'}\n"
            f"{named}/12 players named • {builds}/12 build plans"
        )

    def _refresh_selected_spot(self) -> None:
        row = self.support_table.currentRow()
        if row < 0:
            self._set_selected_spot_empty("Select a spot", "Choose a row to review its jobs.")
            return
        spot = RAID_PLAN_SEATS[row]
        seat_id = _slug(spot)
        try:
            plan = self.current_plan()
            member = plan.member(seat_id)
        except Exception:
            member = None
        if member is None:
            self._set_selected_spot_empty(spot, "No plan state exists for this spot yet.")
            return

        role = _clean(member.role) or "Role not selected"
        eso_class = _clean(member.eso_class)
        self.selected_spot_title.setText(spot)
        self.selected_spot_role.setText(" • ".join(value for value in (role, eso_class) if value))
        self._set_selected_role_icon(role)
        self.selected_player.setText(_clean(member.gamertag) or "Recruitment Needed")
        self.selected_character.setText(_clean(member.character_name) or "Not selected")
        support = " • ".join(
            value for value in (
                _clean(member.primary_assignment),
                _clean(member.secondary_assignment),
            )
            if value
        )
        self.selected_support.setText(support or "Not set")
        self.selected_utility.setText(
            " • ".join(member.utility_assignments) or "None"
        )
        self.selected_gear.setText(
            " + ".join(member.planned_gear_sets) or "Not assigned"
        )
        self.selected_build.setText(_clean(member.selected_build_name) or "Not selected")

        self._selected_note_seat = seat_id
        self._loading_assignment_source = True
        source = self._assignment_source_by_seat.get(
            seat_id,
            _clean(member.assignment_source),
        )
        self.selected_assignment_source.setText(source)
        self._loading_assignment_source = False
        self._loading_selected_notes = True
        note = self._notes_by_seat.get(seat_id, _clean(member.notes))
        self.selected_notes.setPlainText(note)
        self._loading_selected_notes = False

    def current_plan(self):
        plan = super().current_plan()
        if not hasattr(self, "_utility_by_seat"):
            return plan
        members = []
        for member in plan.members:
            seat_id = member.seat_id.casefold()
            utilities = self._utility_by_seat.get(
                seat_id,
                tuple(member.utility_assignments),
            )
            note = self._notes_by_seat.get(
                seat_id,
                _clean(member.notes),
            )
            assignment_source = self._assignment_source_by_seat.get(
                seat_id,
                _clean(member.assignment_source),
            )
            members.append(
                member.with_selection(
                    utility_assignments=tuple(utilities),
                    assignment_source=assignment_source or None,
                    notes=note or None,
                )
            )
        return replace(plan, members=tuple(members))

    def apply_plan(self, plan) -> None:
        super().apply_plan(plan)
        self._utility_by_seat = {
            member.seat_id.casefold(): tuple(member.utility_assignments)
            for member in plan.members
        }
        self._notes_by_seat = {
            member.seat_id.casefold(): _clean(member.notes)
            for member in plan.members
        }
        self._assignment_source_by_seat = {
            member.seat_id.casefold(): _clean(member.assignment_source)
            for member in plan.members
        }
        if hasattr(self, "support_table"):
            members = {member.seat_id.casefold(): member for member in plan.members}
            for row, spot in enumerate(RAID_PLAN_SEATS):
                member = members.get(_slug(spot).casefold())
                primary, secondary = self._support_combos(row)
                for combo, value in (
                    (primary, member.primary_assignment if member else ""),
                    (secondary, member.secondary_assignment if member else ""),
                ):
                    if combo is not None:
                        combo.blockSignals(True)
                        combo.setCurrentText(_clean(value))
                        combo.blockSignals(False)
                utility = self.utility_table.cellWidget(row, 2)
                if isinstance(utility, QComboBox):
                    utility.blockSignals(True)
                    value = member.utility_assignments[0] if member and member.utility_assignments else ""
                    utility.setCurrentText(value)
                    utility.blockSignals(False)
            self._refresh_city_assignment_rows()
        self._navigation_baseline_plan = self.current_plan()

    def clear_plan(self) -> None:
        super().clear_plan()
        self._utility_by_seat.clear()
        self._notes_by_seat.clear()
        self._assignment_source_by_seat.clear()
        if hasattr(self, "support_table"):
            for row in range(len(RAID_PLAN_SEATS)):
                primary, secondary = self._support_combos(row)
                for combo in (primary, secondary):
                    if combo is not None:
                        combo.setCurrentText("")
                utility = self.utility_table.cellWidget(row, 2)
                if isinstance(utility, QComboBox):
                    utility.setCurrentText("")
            self._refresh_city_assignment_rows()

    def save_current_plan(self) -> None:
        super().save_current_plan()
        if hasattr(self, "assignment_summary_label"):
            self._refresh_city_assignment_rows()


__all__ = ["CityRaidAssignmentsPage", "_role_icon_name", "_role_icon_pixmap"]
