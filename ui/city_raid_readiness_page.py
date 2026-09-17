from __future__ import annotations

"""Urban Wilderness Readiness surface for one persisted RaidPlan.

The page composes only evidence it can actually prove from current persisted state.
Build/assignment presence is known from RaidPlan. Rotation, sustain, and coverage remain
NEEDS REVIEW until their owning engines provide evidence. Human Ready is explicit user state.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir, get_resource_path
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_repository import RaidPlanRepository
from services.raid_section_state_service import RaidSectionStateService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


def _clean(value: object) -> str:
    return str(value or "").strip()


def _known(value: bool) -> str:
    # Text + shape semantics are intentional: readiness never depends on red/green alone.
    return "✓ READY" if value else "! GAP"


def _unknown() -> str:
    return "○ NEEDS REVIEW"


class _ReadinessArt(QLabel):
    """Fixed-height field-journal sketch for parchment cards.

    Parchment cards deliberately use the monochrome/pencil field-journal family only.
    Full-color city artwork belongs on dark surfaces and never controls card geometry.
    """

    def __init__(self, filename: str, fallback: str, parent=None) -> None:
        super().__init__(parent)
        self.filename = filename
        self.fallback = fallback
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("readinessNoteArt", True)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        path = get_resource_path(
            "assets", "themes", "bff", "field_journal", "roster", self.filename
        )
        pixmap = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
        self.clear()
        if pixmap.isNull():
            self.setText(self.fallback)
            self.setToolTip("")
            return
        self.setPixmap(
            pixmap.scaled(
                max(240, self.width() or 320),
                138,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.setToolTip(self.fallback)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()


class CityRaidReadinessPage(FoundryPage):
    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self.user_state = RaidSectionStateService()
        self._plan: RaidPlan | None = None
        self._build_ui()
        self.refresh_plans()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Readiness",
            subtitle="Know what is ready before the pull teaches it to you.",
            department="RAID • READINESS",
            icon="checklist",
        )
        self.set_header(self.header)

        self.plan_combo = QComboBox()
        self.plan_combo.setMinimumWidth(260)
        self.plan_combo.currentIndexChanged.connect(self._load_selected_plan)
        self.header.add_context_widget(self.plan_combo)
        refresh = QPushButton("Refresh Evidence")
        refresh.setProperty("primary", True)
        refresh.clicked.connect(self.refresh_plans)
        self.header.add_context_widget(refresh)

        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        filters = FoundryCard("Readiness Filters", "checklist")
        self.gaps_only = QCheckBox("Show Gaps Only")
        self.gaps_only.toggled.connect(self._render_plan)
        filters.addWidget(self.gaps_only)
        for text in ("Tanks", "Healers", "Damage", "Support"):
            item = QCheckBox(text)
            item.setChecked(True)
            item.setEnabled(False)
            filters.addWidget(item)
        left_layout.addWidget(filters)
        self.summary_card = FoundryCard("Summary", "group")
        self.summary_label = QLabel("No Raid Plan selected.")
        self.summary_label.setWordWrap(True)
        self.summary_card.addWidget(self.summary_label)
        left_layout.addWidget(self.summary_card)

        field_note = FoundryCard("Field Note", "feather")
        field_note.setProperty("parchment", True)
        field_note.addWidget(
            _ReadinessArt(
                "roster_people.jpg",
                "Ready means proven or explicitly confirmed. Unknown is allowed to stay unknown.",
            )
        )
        left_layout.addWidget(field_note)
        left_layout.addStretch(1)
        root.addWidget(left, 2)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        matrix = FoundryCard("Plan Health Matrix", "shield")
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Build", "Assignment", "Rotation", "Sustain", "Coverage", "Human Ready", "Notes")
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._refresh_selected_gap)
        matrix.addWidget(self.table)
        center_layout.addWidget(matrix, 4)

        bottom = QHBoxLayout()
        blockers = FoundryCard("Blockers & Gaps", "warning")
        self.blockers_label = QLabel("Select a plan to review gaps.")
        self.blockers_label.setWordWrap(True)
        blockers.addWidget(self.blockers_label)
        bottom.addWidget(blockers, 1)
        activity = FoundryCard("Recent Readiness Activity", "clipboard")
        self.activity_label = QLabel("No manual readiness changes yet.")
        self.activity_label.setWordWrap(True)
        activity.addWidget(self.activity_label)
        bottom.addWidget(activity, 1)
        center_layout.addLayout(bottom, 2)
        root.addWidget(center, 7)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        selected = FoundryCard("Selected Gap", "warning")
        self.selected_label = QLabel("Select a spot in the matrix.")
        self.selected_label.setWordWrap(True)
        selected.addWidget(self.selected_label)
        open_build = QPushButton("Open Build")
        open_build.clicked.connect(lambda: self.pageRequested.emit("console:2"))
        selected.addWidget(open_build)
        open_rotation = QPushButton("Open Rotation")
        open_rotation.clicked.connect(lambda: self.pageRequested.emit("rotations"))
        selected.addWidget(open_rotation)
        open_coverage = QPushButton("Open Coverage")
        open_coverage.clicked.connect(lambda: self.pageRequested.emit("console:7"))
        selected.addWidget(open_coverage)
        self.mark_ready = QPushButton("Mark Human Ready")
        self.mark_ready.setProperty("primary", True)
        self.mark_ready.clicked.connect(self._toggle_human_ready)
        selected.addWidget(self.mark_ready)
        right_layout.addWidget(selected)

        fun_note = FoundryCard("Run Note", "feather")
        fun_note.setProperty("parchment", True)
        fun_note.addWidget(
            _ReadinessArt(
                "roster_team.jpg",
                "A ready group is just panic that has been alphabetized.",
            )
        )
        right_layout.addWidget(fun_note)
        right_layout.addStretch(1)
        root.addWidget(right, 3)

        self.add_workspace(body)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def refresh_plans(self) -> None:
        current = self.plan_combo.currentData()
        plans = self.repository.list_plans()
        self.plan_combo.blockSignals(True)
        self.plan_combo.clear()
        for plan in plans:
            self.plan_combo.addItem(f"{plan.name} • {plan.trial_id}", plan.plan_id)
        if current:
            index = self.plan_combo.findData(current)
            if index >= 0:
                self.plan_combo.setCurrentIndex(index)
        self.plan_combo.blockSignals(False)
        self._load_selected_plan()

    def _load_selected_plan(self, *_args) -> None:
        plan_id = self.plan_combo.currentData()
        self._plan = self.repository.get(plan_id) if isinstance(plan_id, str) and plan_id else None
        self._render_plan()

    @staticmethod
    def _row_gap(member: RaidPlanMember, human_ready: bool | None) -> bool:
        return not member.build_selected or not bool(member.primary_assignment or member.secondary_assignment) or human_ready is not True

    def _render_plan(self, *_args) -> None:
        plan = self._plan
        self.table.setRowCount(0)
        if plan is None:
            self.summary_label.setText("No Raid Plan selected.")
            self.blockers_label.setText("No plan evidence to review.")
            self.selected_label.setText("Select a saved Raid Plan first.")
            return

        gaps: list[str] = []
        ready_count = 0
        for member in plan.members:
            human = self.user_state.human_ready(plan.plan_id, member.seat_id)
            if self.gaps_only.isChecked() and not self._row_gap(member, human):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            build_ok = member.build_selected
            assignment_ok = bool(member.primary_assignment or member.secondary_assignment)
            human_text = "✓ READY" if human is True else "! NOT READY" if human is False else "○ NEEDS REVIEW"
            notes = []
            if not build_ok:
                notes.append("Build missing")
                gaps.append(f"{member.seat_id}: build not selected")
            if not assignment_ok:
                notes.append("Assignment missing")
                gaps.append(f"{member.seat_id}: assignment missing")
            if human is not True:
                notes.append("Player confirmation pending")
                gaps.append(f"{member.seat_id}: human confirmation pending")
            else:
                ready_count += 1
            values = (
                member.seat_id.replace("-", " ").title(),
                member.gamertag,
                _known(build_ok),
                _known(assignment_ok),
                _unknown(),
                _unknown(),
                _unknown(),
                human_text,
                "; ".join(notes) or "Known fields ready; engine evidence still needs review",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, member.seat_id if col == 0 else None)
                self.table.setItem(row, col, item)

        total = len(plan.members)
        self.summary_label.setText(
            f"{total} total spots\n{ready_count} human-confirmed\n{max(0, total - ready_count)} awaiting confirmation\n\n"
            "Rotation / Sustain / Coverage are deliberately shown as NEEDS REVIEW until their owning engines supply evidence."
        )
        self.blockers_label.setText("\n".join(f"• {gap}" for gap in gaps[:10]) if gaps else "No build, assignment, or human-confirmation gaps.")
        events = self.user_state.events(plan.plan_id, limit=6)
        self.activity_label.setText("\n".join(f"{event.evidence}  {event.text}" for event in events) or "No manual readiness changes yet.")
        self.status.info(f"Readiness loaded for {plan.name}. Unknown engine evidence remains explicit.")
        self._refresh_selected_gap()

    def _selected_member(self) -> RaidPlanMember | None:
        if self._plan is None:
            return None
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        seat_id = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        return self._plan.member(str(seat_id or ""))

    def _refresh_selected_gap(self) -> None:
        member = self._selected_member()
        if member is None or self._plan is None:
            self.selected_label.setText("Select a spot in the matrix.")
            return
        human = self.user_state.human_ready(self._plan.plan_id, member.seat_id)
        self.selected_label.setText(
            f"{member.seat_id.replace('-', ' ').title()}\n"
            f"Player: {member.gamertag}\n"
            f"Character: {_clean(member.character_name) or 'Not selected'}\n"
            f"Role: {_clean(member.role) or 'Not selected'}\n"
            f"Build: {_clean(member.selected_build_name) or 'Not selected'}\n"
            f"Assignment: {_clean(member.primary_assignment) or 'Not set'}\n"
            f"Secondary: {_clean(member.secondary_assignment) or 'Not set'}\n"
            f"Human Ready: {'Ready' if human is True else 'Not ready' if human is False else 'Needs review'}\n\n"
            "Rotation / sustain / coverage evidence is not inferred here."
        )
        self.mark_ready.setText("Clear Human Ready" if human is True else "Mark Human Ready")

    def _toggle_human_ready(self) -> None:
        member = self._selected_member()
        if member is None or self._plan is None:
            self.status.warning("Select a Raid Plan spot first.")
            return
        current = self.user_state.human_ready(self._plan.plan_id, member.seat_id)
        value = None if current is True else True
        self.user_state.set_human_ready(self._plan.plan_id, member.seat_id, value)
        self.user_state.add_event(
            self._plan.plan_id,
            "human_ready",
            f"{member.gamertag} {'marked human ready' if value is True else 'human-ready confirmation cleared'}",
            evidence="MANUAL",
        )
        self._render_plan()


__all__ = ["CityRaidReadinessPage"]
