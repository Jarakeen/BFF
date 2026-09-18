from __future__ import annotations

"""City After Midnight Live Raid surface.

The page is intentionally strict about evidence. RaidPlan values are PLANNED, button-driven
run state is MANUAL, and no live telemetry is invented for health, position, casts, buffs,
or ultimate percentage.
"""

from datetime import datetime, timezone

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from models.raid_plan import RaidPlan
from services.raid_plan_repository import RaidPlanRepository
from services.raid_section_state_service import RaidSectionStateService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_trial_banner_support import TrialBannerLabel, trial_banner_path


def _clean(value: object) -> str:
    return str(value or "").strip()


def _parse_iso(value: object) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class CityLiveRaidPage(FoundryPage):
    pageRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.repository = RaidPlanRepository(get_data_dir() / "raid_plans.json")
        self.user_state = RaidSectionStateService()
        self._plan: RaidPlan | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_clock)
        self._build_ui()
        self.refresh_plans()
        self._timer.start()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Live Raid",
            subtitle="Keep the group steady while the city catches fire.",
            department="RAID • LIVE",
            icon="stopwatch",
        )
        self.set_header(self.header)

        self.plan_combo = QComboBox()
        self.plan_combo.setMinimumWidth(260)
        self.plan_combo.currentIndexChanged.connect(self._load_selected_plan)
        self.header.add_context_widget(self.plan_combo)

        self.start_button = QPushButton("Start Pull")
        self.start_button.setProperty("primary", True)
        self.start_button.clicked.connect(self._start_pull)
        self.header.add_context_widget(self.start_button)
        self.pause_button = QPushButton("Pause Notes")
        self.pause_button.clicked.connect(self._pause_notes)
        self.header.add_context_widget(self.pause_button)
        self.end_button = QPushButton("End Attempt")
        self.end_button.setProperty("danger", True)
        self.end_button.clicked.connect(self._end_attempt)
        self.header.add_context_widget(self.end_button)

        hero = FoundryCard("Current Encounter", "trial")
        hero_row = QHBoxLayout()
        hero_row.setSpacing(12)
        self.hero_art = TrialBannerLabel()
        self.hero_art.hide()
        hero_row.addWidget(self.hero_art, 3)
        self.hero_title = QLabel("No Raid Plan selected")
        self.hero_title.setProperty("heroTitle", True)
        self.hero_title.setWordWrap(True)
        hero_row.addWidget(self.hero_title, 4)
        self.phase_label = QLabel("PLANNED\nPhase: —")
        self.phase_label.setWordWrap(True)
        hero_row.addWidget(self.phase_label, 1)
        self.timer_label = QLabel("MANUAL\nPull 00:00")
        self.timer_label.setWordWrap(True)
        hero_row.addWidget(self.timer_label, 1)
        self.attempt_label = QLabel("MANUAL\nAttempt #0")
        self.attempt_label.setWordWrap(True)
        hero_row.addWidget(self.attempt_label, 1)
        self.combat_label = QLabel("MANUAL\nNot in pull")
        self.combat_label.setWordWrap(True)
        hero_row.addWidget(self.combat_label, 1)
        hero.addLayout(hero_row)
        evidence = QLabel("Evidence key: PLANNED = RaidPlan intent · MANUAL = button/user state · OBSERVED = external telemetry (none connected here)")
        evidence.setProperty("muted", True)
        evidence.setWordWrap(True)
        hero.addWidget(evidence)
        self.workspace_layout.addWidget(hero)

        middle = QHBoxLayout()
        spots = FoundryCard("Raid Spots", "group")
        self.spots_table = QTableWidget(0, 8)
        self.spots_table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Assignment", "Status", "Ult", "Notes", "Alive", "Evidence")
        )
        self.spots_table.verticalHeader().setVisible(False)
        self.spots_table.horizontalHeader().setStretchLastSection(True)
        self.spots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        spots.addWidget(self.spots_table)
        view_assignments = QPushButton("View Assignments")
        view_assignments.clicked.connect(lambda: self.pageRequested.emit("assignments"))
        spots.addWidget(view_assignments)
        middle.addWidget(spots, 3)

        callouts = FoundryCard("Current Callouts", "warning")
        self.callouts_label = QLabel("No planned callouts for this Raid Plan.")
        self.callouts_label.setWordWrap(True)
        callouts.addWidget(self.callouts_label)
        middle.addWidget(callouts, 2)
        self.workspace_layout.addLayout(middle)

        lower = QHBoxLayout()
        timeline = FoundryCard("Next 60 Seconds", "stopwatch")
        timeline_text = QLabel(
            "No live encounter clock is connected. Reviewed trigger responsibilities appear as PLANNED conditions, never fabricated timestamps."
        )
        timeline_text.setWordWrap(True)
        timeline.addWidget(timeline_text)
        lower.addWidget(timeline, 2)

        notes = FoundryCard("Quick Notes / Run Sheet", "clipboard")
        self.run_notes_edit = QTextEdit()
        self.run_notes_edit.setAcceptRichText(False)
        self.run_notes_edit.setPlaceholderText("Add manual pull notes, reminders, or observations…")
        self.run_notes_edit.setMaximumHeight(135)
        notes.addWidget(self.run_notes_edit)
        self.save_run_notes_button = QPushButton("Save Run Notes")
        self.save_run_notes_button.setProperty("primary", True)
        self.save_run_notes_button.clicked.connect(self._save_run_notes)
        notes.addWidget(self.save_run_notes_button)
        lower.addWidget(notes, 2)

        coverage = FoundryCard("Coverage Snapshot", "shield")
        self.coverage_label = QLabel("NEEDS REVIEW\nOpen Coverage for authoritative provider evidence.")
        self.coverage_label.setWordWrap(True)
        coverage.addWidget(self.coverage_label)
        open_coverage = QPushButton("Open Coverage")
        open_coverage.clicked.connect(lambda: self.pageRequested.emit("console:7"))
        coverage.addWidget(open_coverage)
        lower.addWidget(coverage, 2)

        recent = FoundryCard("Recent Events", "archive")
        self.events_label = QLabel("No manual run events yet.")
        self.events_label.setWordWrap(True)
        recent.addWidget(self.events_label)
        lower.addWidget(recent, 2)
        self.workspace_layout.addLayout(lower)

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

    def _render_plan(self) -> None:
        plan = self._plan
        self.spots_table.setRowCount(0)
        if plan is None:
            self.hero_art.set_source(None)
            self.hero_title.setText("No Raid Plan selected")
            self.callouts_label.setText("No planned callouts for this Raid Plan.")
            self.events_label.setText("No manual run events yet.")
            self.run_notes_edit.clear()
            self.run_notes_edit.setEnabled(False)
            self.save_run_notes_button.setEnabled(False)
            return
        self.hero_art.set_source(trial_banner_path(plan.trial_id, plan.name))
        if not self.run_notes_edit.hasFocus():
            self.run_notes_edit.setPlainText(self.user_state.run_notes(plan.plan_id))
        self.hero_title.setText(
            f"{plan.name}\n{plan.trial_id} · {plan.difficulty or 'Difficulty not set'} · {len(plan.members)} planned players"
        )
        for member in plan.members:
            row = self.spots_table.rowCount()
            self.spots_table.insertRow(row)
            assignment = " / ".join(
                value for value in (_clean(member.primary_assignment), _clean(member.secondary_assignment)) if value
            ) or "Not assigned"
            values = (
                member.seat_id.replace("-", " ").title(),
                member.gamertag,
                assignment,
                "PLANNED",
                "—",
                _clean(member.notes) or "",
                "—",
                "PLANNED",
            )
            for col, value in enumerate(values):
                self.spots_table.setItem(row, col, QTableWidgetItem(value))

        callout_lines = []
        for item in plan.triggered_responsibilities:
            callout_lines.append(
                f"PLANNED  {item.trigger_key} → {item.seat_id}: {item.directive}"
            )
        self.callouts_label.setText("\n".join(callout_lines) if callout_lines else "No planned trigger responsibilities on this Raid Plan.")
        self._refresh_run_state()
        self._refresh_events()
        self.status.info(f"Live Raid loaded {plan.name}. Runtime telemetry is not inferred.")

    def _refresh_run_state(self) -> None:
        if self._plan is None:
            return
        state = self.user_state.run_state(self._plan.plan_id)
        active = bool(state.get("active", False))
        attempt = int(state.get("attempt", 0) or 0)
        paused = bool(state.get("notes_paused", False))
        self.attempt_label.setText(f"MANUAL\nAttempt #{attempt}")
        self.combat_label.setText("MANUAL\nPull active" if active else "MANUAL\nNot in pull")
        self.pause_button.setText("Resume Notes" if paused else "Pause Notes")
        self.start_button.setEnabled(not active)
        self.end_button.setEnabled(active)
        self.run_notes_edit.setEnabled(not paused)
        self.save_run_notes_button.setEnabled(not paused)
        self._refresh_clock()

    def _refresh_clock(self) -> None:
        if self._plan is None:
            self.timer_label.setText("MANUAL\nPull 00:00")
            return
        state = self.user_state.run_state(self._plan.plan_id)
        if not state.get("active"):
            self.timer_label.setText("MANUAL\nPull 00:00")
            return
        started = _parse_iso(state.get("started_at"))
        if started is None:
            self.timer_label.setText("MANUAL\nPull --:--")
            return
        seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
        minutes, second = divmod(seconds, 60)
        self.timer_label.setText(f"MANUAL\nPull {minutes:02d}:{second:02d}")

    def _refresh_events(self) -> None:
        if self._plan is None:
            return
        rows = self.user_state.events(self._plan.plan_id, limit=9)
        self.events_label.setText(
            "\n".join(f"{event.evidence}  {event.text}" for event in rows) or "No manual run events yet."
        )

    def _save_run_notes(self) -> None:
        if self._plan is None:
            self.status.warning("Select a Raid Plan before saving run notes.")
            return
        notes = self.run_notes_edit.toPlainText().strip()
        state = self.user_state.set_run_notes(self._plan.plan_id, notes)
        attempt = int(state.get("attempt", 0) or 0)
        archived = self.user_state.save_review_note(
            plan_id=self._plan.plan_id,
            trial_id=self._plan.trial_id,
            plan_name=self._plan.name,
            attempt=attempt,
            notes=notes,
            started_at=_clean(state.get("started_at")),
            ended_at=_clean(state.get("ended_at")),
        )
        if archived is None:
            self.status.info("Blank notes cleared from the active Raid Plan.")
        else:
            label = f"attempt #{attempt}" if attempt else "general note"
            self.status.info(f"Run notes saved to Review for {label}.")
        self._refresh_events()

    def _start_pull(self) -> None:
        if self._plan is None:
            self.status.warning("Select a Raid Plan before starting a pull.")
            return
        self.user_state.start_pull(self._plan.plan_id)
        self._refresh_run_state()
        self._refresh_events()

    def _pause_notes(self) -> None:
        if self._plan is None:
            return
        state = self.user_state.run_state(self._plan.plan_id)
        self.user_state.set_notes_paused(self._plan.plan_id, not bool(state.get("notes_paused", False)))
        self._refresh_run_state()
        self._refresh_events()

    def _end_attempt(self) -> None:
        if self._plan is None:
            return
        self.user_state.end_attempt(self._plan.plan_id)
        self._refresh_run_state()
        self._refresh_events()


__all__ = ["CityLiveRaidPage"]
