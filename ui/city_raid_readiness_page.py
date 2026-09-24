from __future__ import annotations

"""Urban Wilderness Readiness surface for one persisted RaidPlan.

The page composes only evidence it can actually prove from current persisted state.
Build/assignment presence is known from RaidPlan. Rotation, sustain, and coverage remain
NEEDS REVIEW until their owning engines provide evidence. Human Ready is explicit user state.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import DEFAULT_DATABASE, get_data_dir, get_resource_path, get_user_database_path, get_settings_path
from models.raid_plan import RaidPlan, RaidPlanMember
from services.finch_shared_provenance_service import format_shared_timestamp
from services.finch_shared_readiness_service import (
    list_shared_readiness_from_finch,
    publish_readiness_to_finch,
)
from services.raid_plan_repository import RaidPlanRepository
from services.raid_readiness_evidence_service import RaidReadinessEvidenceService
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
    """Fixed-height Urban Wilderness pencil art that never owns layout geometry."""

    def __init__(self, filename: str, fallback: str, parent=None) -> None:
        super().__init__(parent)
        self.filename = filename
        self.fallback = fallback
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setFixedHeight(150)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setProperty("readinessNoteArt", True)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        path = get_resource_path(
            "assets", "themes", "bff", "urban_wilderness", "notes", self.filename
        )
        pixmap = QPixmap(str(path)) if Path(path).is_file() else QPixmap()
        self.clear()
        if pixmap.isNull():
            self.setText(self.fallback)
            self.setToolTip("")
            return

        target_width = max(1, self.width())
        target_height = 138
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - target_width) // 2)
        y = max(0, (scaled.height() - target_height) // 2)
        self.setPixmap(
            scaled.copy(
                x,
                y,
                min(target_width, scaled.width()),
                min(target_height, scaled.height()),
            )
        )
        self.setToolTip(self.fallback)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()


_FINCH_READINESS_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="finch-readiness",
)


class CityRaidReadinessPage(FoundryPage):
    pageRequested = Signal(str)
    buildRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.repository = RaidPlanRepository(get_user_database_path())
        self.user_state = RaidSectionStateService()
        self.readiness_evidence = RaidReadinessEvidenceService(
            data_dir=get_data_dir(),
            database_path=DEFAULT_DATABASE,
        )
        self._plan: RaidPlan | None = None
        self._evidence = None
        self._finch_publish_future: Future | None = None
        self._finch_shared_future: Future | None = None
        self._finch_publish_timer = QTimer(self)
        self._finch_publish_timer.setInterval(100)
        self._finch_publish_timer.timeout.connect(self._poll_finch_publish)
        self._finch_shared_timer = QTimer(self)
        self._finch_shared_timer.setInterval(100)
        self._finch_shared_timer.timeout.connect(self._poll_finch_shared)
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

        self.publish_finch = QPushButton("Publish Readiness")
        self.publish_finch.clicked.connect(self._publish_readiness_to_finch)
        self.header.add_context_widget(self.publish_finch)
        self.get_shared_finch = QPushButton("Get Shared Readiness")
        self.get_shared_finch.clicked.connect(self._get_shared_readiness_from_finch)
        self.header.add_context_widget(self.get_shared_finch)

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
                "note1.png",
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
        open_build.clicked.connect(self._open_selected_build)
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
                "note4.png",
                "A ready group is just panic that has been alphabetized.",
            )
        )
        right_layout.addWidget(fun_note)
        right_layout.addStretch(1)
        root.addWidget(right, 3)

        self.add_workspace(body)
        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def _publish_readiness_to_finch(self) -> None:
        plan = self._plan
        if plan is None:
            self.status.warning("Select a saved Raid Plan before publishing Readiness.")
            return
        if self._finch_publish_future is not None and not self._finch_publish_future.done():
            self.status.info("Finch Readiness publish is already running.")
            return

        self.publish_finch.setEnabled(False)
        self.status.info(f"Publishing Readiness for {plan.name} to Finch…")
        self._finch_publish_future = _FINCH_READINESS_EXECUTOR.submit(
            publish_readiness_to_finch,
            plan_id=plan.plan_id,
            raid_plans_path=self.repository.path,
            data_dir=get_data_dir(),
            database_path=DEFAULT_DATABASE,
            settings_path=get_settings_path(),
        )
        self._finch_publish_timer.start()

    def _poll_finch_publish(self) -> None:
        future = self._finch_publish_future
        if future is None or not future.done():
            return
        self._finch_publish_timer.stop()
        self.publish_finch.setEnabled(True)
        self._finch_publish_future = None
        try:
            result = future.result()
        except Exception as exc:
            self.status.warning(
                f"Finch Readiness publish failed: {type(exc).__name__}: {exc}"
            )
            return
        self.status.success(
            f"Published Readiness to Finch: {result.snapshot_key}."
        )

    def _get_shared_readiness_from_finch(self) -> None:
        if self._finch_shared_future is not None and not self._finch_shared_future.done():
            self.status.info("Finch shared Readiness fetch is already running.")
            return

        self.get_shared_finch.setEnabled(False)
        self.status.info("Getting shared Readiness from Finch…")
        self._finch_shared_future = _FINCH_READINESS_EXECUTOR.submit(
            list_shared_readiness_from_finch,
            data_dir=get_data_dir(),
            database_path=DEFAULT_DATABASE,
            settings_path=get_settings_path(),
        )
        self._finch_shared_timer.start()

    def _poll_finch_shared(self) -> None:
        future = self._finch_shared_future
        if future is None or not future.done():
            return
        self._finch_shared_timer.stop()
        self.get_shared_finch.setEnabled(True)
        self._finch_shared_future = None
        try:
            previews = tuple(future.result())
        except Exception as exc:
            self.status.warning(
                f"Finch shared Readiness fetch failed: {type(exc).__name__}: {exc}"
            )
            return
        if not previews:
            self.status.info("Finch has no shared Readiness snapshots.")
            return

        labels = [
            (
                f"{row.name or row.plan_id} • {row.trial_id or 'Trial unknown'} • "
                f"{row.human_ready}/{row.total} human ready • "
                f"{row.published_by or 'Unknown publisher'} • "
                f"{format_shared_timestamp(row.updated_at)}"
            )
            for row in previews
        ]
        selected, accepted = QInputDialog.getItem(
            self,
            "Shared Readiness on Finch",
            "View shared Readiness snapshot:",
            labels,
            0,
            False,
        )
        if not accepted:
            self.status.info("Shared Readiness view cancelled.")
            return
        try:
            row = previews[labels.index(selected)]
        except (ValueError, IndexError):
            self.status.warning("The selected shared Readiness snapshot is unavailable.")
            return

        QMessageBox.information(
            self,
            "Shared Readiness",
            (
                f"{row.name or row.plan_id}\n"
                f"Trial: {row.trial_id or 'Unknown'}\n"
                f"Team: {row.team_name or 'Not set'}\n"
                f"Published by: {row.published_by or 'Unknown'}\n"
                f"Updated: {format_shared_timestamp(row.updated_at)}\n\n"
                f"Builds: {row.build_ready} ready, {row.build_planned} planned, "
                f"{row.build_gaps} gaps\n"
                f"Assignments: {row.assignment_ready}/{row.total} assigned\n"
                f"Coverage: {row.coverage_covered} covered, {row.coverage_gaps} gaps\n"
                f"Human Ready: {row.human_ready}/{row.total} "
                f"({row.human_pending} pending)\n\n"
                "This is a read-only Finch snapshot. Local Readiness was not changed."
            ),
        )
        self.status.info(
            f"Viewed shared Readiness for {row.name or row.plan_id}; local state unchanged."
        )

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
    def _row_gap(member: RaidPlanMember, human_ready: bool | None, evidence=None) -> bool:
        build_gap = (
            evidence is None
            or str(getattr(evidence, "build_state", "gap")) != "ready"
        )
        coverage_gap = (
            evidence is not None
            and str(getattr(evidence, "coverage_state", "")) == "gap"
        )
        return (
            build_gap
            or coverage_gap
            or not bool(member.primary_assignment or member.secondary_assignment)
            or human_ready is not True
        )

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
        try:
            self._evidence = self.readiness_evidence.evaluate(plan)
        except Exception as exc:
            self._evidence = None
            self.status.warning(
                f"Readiness build/coverage evidence could not be composed: {type(exc).__name__}: {exc}"
            )

        for member in plan.members:
            human = self.user_state.human_ready(plan.plan_id, member.seat_id)
            evidence = self._evidence.seat(member.seat_id) if self._evidence is not None else None
            if self.gaps_only.isChecked() and not self._row_gap(member, human, evidence):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            assignment_ok = bool(member.primary_assignment or member.secondary_assignment)
            human_text = "✓ READY" if human is True else "! NOT READY" if human is False else "○ NEEDS REVIEW"
            build_text = evidence.build_label if evidence is not None else _unknown()
            coverage_text = evidence.coverage_label if evidence is not None else _unknown()
            notes = []
            if evidence is None:
                notes.append("Build / coverage evidence unavailable")
            elif evidence.build_state != "ready":
                notes.append(evidence.build_detail)
                gaps.append(f"{member.seat_id}: {evidence.build_detail}")
            if not assignment_ok:
                notes.append("Assignment missing")
                gaps.append(f"{member.seat_id}: assignment missing")
            if evidence is not None and evidence.coverage_state == "gap":
                notes.append(evidence.coverage_detail)
                gaps.append(f"{member.seat_id}: {evidence.coverage_detail}")
            if human is not True:
                notes.append("Player confirmation pending")
                gaps.append(f"{member.seat_id}: human confirmation pending")
            else:
                ready_count += 1
            values = (
                member.seat_id.replace("-", " ").title(),
                member.gamertag,
                build_text,
                _known(assignment_ok),
                _unknown(),
                _unknown(),
                coverage_text,
                human_text,
                "; ".join(notes) or "Known persisted fields ready; runtime evidence remains separate",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, member.seat_id if col == 0 else None)
                self.table.setItem(row, col, item)

        total = len(plan.members)
        self.summary_label.setText(
            f"{total} total spots\n{ready_count} human-confirmed\n{max(0, total - ready_count)} awaiting confirmation\n\n"
            "Build and Coverage use persisted canonical/planned evidence. Rotation and Sustain remain NEEDS REVIEW until their owning engines supply evidence."
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
        evidence = self._evidence.seat(member.seat_id) if self._evidence is not None else None
        build_detail = (
            evidence.build_detail if evidence is not None else "Evidence unavailable"
        )
        coverage_detail = (
            evidence.coverage_detail if evidence is not None else "Evidence unavailable"
        )
        self.selected_label.setText(
            f"{member.seat_id.replace('-', ' ').title()}\n"
            f"Player: {member.gamertag}\n"
            f"Character: {_clean(member.character_name) or 'Not selected'}\n"
            f"Role: {_clean(member.role) or 'Not selected'}\n"
            f"Build: {evidence.build_label if evidence is not None else _unknown()}\n"
            f"Build detail: {build_detail}\n"
            f"Assignment: {_clean(member.primary_assignment) or 'Not set'}\n"
            f"Secondary: {_clean(member.secondary_assignment) or 'Not set'}\n"
            f"Coverage: {evidence.coverage_label if evidence is not None else _unknown()}\n"
            f"Coverage detail: {coverage_detail}\n"
            f"Human Ready: {'Ready' if human is True else 'Not ready' if human is False else 'Needs review'}\n\n"
            "Rotation / sustain evidence remains unresolved until its owning engines supply it."
        )
        self.mark_ready.setText("Clear Human Ready" if human is True else "Mark Human Ready")

    def _open_selected_build(self) -> None:
        member = self._selected_member()
        if member is None:
            self.status.warning("Select a Raid Plan spot first.")
            return
        build_id = _clean(member.selected_build_id)
        if build_id:
            self.buildRequested.emit(build_id)
            return
        self.status.warning(
            "This chair does not have a canonical selected build yet. Save the Comp plan first."
        )

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
