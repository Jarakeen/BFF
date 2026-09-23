from __future__ import annotations

"""City After Midnight Live Raid surface.

The page is intentionally strict about evidence. RaidPlan values are PLANNED, button-driven
run state is MANUAL, and no live telemetry is invented for health, position, casts, buffs,
or ultimate percentage.
"""

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir, get_user_database_path
from models.raid_plan import RaidPlan
from services.encounter_raid_map_store import EncounterRaidMapStore
from services.live_raid_encounter_projection_service import (
    LiveRaidEncounterContext,
    LiveRaidEncounterProjectionService,
)
from services.raid_plan_repository import RaidPlanRepository
from services.raid_section_state_service import RaidSectionStateService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage
from ui.raid_trial_banner_support import TrialBannerLabel, trial_banner_path
from ui.ui_safety import (
    confirm_destructive_action,
    confirm_replacement,
    confirm_unsaved_changes,
    mark_save_failed,
    mark_saved,
    mark_saving,
)


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
    raidMapRequested = Signal(str, str)
    bossMechanicsRequested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.repository = RaidPlanRepository(get_user_database_path())
        self.user_state = RaidSectionStateService()
        self.encounter_projection = LiveRaidEncounterProjectionService(
            get_data_dir() / "eso.db",
            get_data_dir(),
        )
        self.raid_map_store = EncounterRaidMapStore(get_data_dir())
        self._raid_map_source_pixmap = QPixmap()
        self._raid_map_zoom = 1.0
        self._plan: RaidPlan | None = None
        self._run_notes_baseline = ""
        self._encounter_context: LiveRaidEncounterContext | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_clock)
        self._build_ui()
        self.refresh_plans()
        self._timer.start()

    def _live_status_tile(self, title: str, value: str, role: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setProperty("liveRaidStatusTile", True)
        tile.setProperty("liveRaidStatusRole", role)
        tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tile.setMinimumHeight(48)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(10, 5, 10, 6)
        layout.setSpacing(1)

        heading = QLabel(title)
        heading.setProperty("liveRaidStatusHeading", True)
        label = QLabel(value)
        label.setProperty("liveRaidStatusValue", True)
        label.setProperty("liveRaidStatusRole", role)
        layout.addWidget(heading)
        layout.addWidget(label)
        return tile, label

    @staticmethod
    def _style_live_card(card: FoundryCard, role: str, *, compact: bool = False) -> FoundryCard:
        card.setProperty("liveRaidCard", True)
        card.setProperty("liveRaidCardRole", role)
        card.set_body_margins(10, 7 if compact else 9, 10, 8 if compact else 10)
        card.set_body_spacing(5)
        if compact:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return card

    def _build_ui(self) -> None:
        self.setProperty("liveRaidPage", True)
        self.header = FoundryHeader(
            title="Live Raid",
            subtitle="Keep the group steady while the city catches fire.",
            department="RAID • LIVE",
            icon="stopwatch",
        )
        self.set_header(self.header)

        self.plan_combo = QComboBox()
        self.plan_combo.setMinimumWidth(260)
        self.plan_combo.setProperty("liveRaidContext", True)
        self.plan_combo.currentIndexChanged.connect(self._load_selected_plan)
        self.header.add_context_widget(self.plan_combo)

        self.encounter_combo = QComboBox()
        self.encounter_combo.setMinimumWidth(220)
        self.encounter_combo.setProperty("liveRaidContext", True)
        self.encounter_combo.currentIndexChanged.connect(self._encounter_changed)
        self.header.add_context_widget(self.encounter_combo)

        self.boss_mechanics_button = QPushButton("Boss Mechanics")
        self.boss_mechanics_button.setProperty("liveRaidAction", "mechanics")
        self.boss_mechanics_button.setToolTip(
            "Open Mechanics & Timelines directly on the currently selected boss."
        )
        self.boss_mechanics_button.clicked.connect(self._open_boss_mechanics)
        self.header.add_context_widget(self.boss_mechanics_button)

        self.start_button = QPushButton("Start Pull")
        self.start_button.setProperty("primary", True)
        self.start_button.setProperty("liveRaidAction", "start")
        self.start_button.clicked.connect(self._start_pull)
        self.header.add_context_widget(self.start_button)
        self.pause_button = QPushButton("Pause Notes")
        self.pause_button.setProperty("liveRaidAction", "pause")
        self.pause_button.clicked.connect(self._pause_notes)
        self.header.add_context_widget(self.pause_button)
        self.end_button = QPushButton("End Attempt")
        self.end_button.setProperty("danger", True)
        self.end_button.setProperty("liveRaidAction", "end")
        self.end_button.clicked.connect(self._end_attempt)
        self.header.add_context_widget(self.end_button)

        hero = self._style_live_card(FoundryCard("Current Encounter", "trial"), "hero")
        hero.setMinimumHeight(150)
        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 0, 0, 0)
        hero_row.setSpacing(12)

        self.hero_art = TrialBannerLabel()
        self.hero_art.setProperty("liveRaidHeroArt", True)
        self.hero_art.setMinimumWidth(210)
        self.hero_art.setMaximumWidth(300)
        self.hero_art.setMinimumHeight(112)
        self.hero_art.hide()
        hero_row.addWidget(self.hero_art, 3)

        identity = QWidget()
        identity.setProperty("liveRaidHeroIdentity", True)
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(2, 2, 2, 2)
        identity_layout.setSpacing(3)
        self.hero_title = QLabel("No Raid Plan selected")
        self.hero_title.setProperty("heroTitle", True)
        self.hero_title.setProperty("liveRaidHeroTitle", True)
        self.hero_title.setWordWrap(True)
        identity_layout.addWidget(self.hero_title)
        self.phase_label = QLabel("Current Phase\n—")
        self.phase_label.setProperty("liveRaidHeroPhase", True)
        self.phase_label.setWordWrap(True)
        identity_layout.addWidget(self.phase_label)
        identity_layout.addStretch(1)
        hero_row.addWidget(identity, 4)

        status_grid = QWidget()
        status_grid.setProperty("liveRaidStatusGrid", True)
        status_layout = QVBoxLayout(status_grid)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        top_status = QHBoxLayout()
        top_status.setSpacing(6)
        combat_tile, self.combat_label = self._live_status_tile("COMBAT", "Not in pull", "combat")
        alive_tile, self.alive_label = self._live_status_tile("TEAM", "Planned roster", "team")
        top_status.addWidget(combat_tile)
        top_status.addWidget(alive_tile)
        status_layout.addLayout(top_status)

        bottom_status = QHBoxLayout()
        bottom_status.setSpacing(6)
        timer_tile, self.timer_label = self._live_status_tile("PULL TIMER", "00:00", "timer")
        attempt_tile, self.attempt_label = self._live_status_tile("ATTEMPT", "#0", "attempt")
        bottom_status.addWidget(timer_tile)
        bottom_status.addWidget(attempt_tile)
        status_layout.addLayout(bottom_status)
        hero_row.addWidget(status_grid, 3)
        hero.addLayout(hero_row)

        evidence = QLabel(
            "PLANNED = Raid Plan intent  •  MANUAL = user/run state  •  OBSERVED = external telemetry (not connected)"
        )
        evidence.setProperty("liveRaidEvidenceKey", True)
        evidence.setWordWrap(True)
        hero.addWidget(evidence)
        self.workspace_layout.addWidget(hero)

        middle = QHBoxLayout()
        middle.setSpacing(10)

        spots = self._style_live_card(FoundryCard("Raid Spots", "group"), "spots")

        self.raid_spots_tabs = QTabWidget()
        self.raid_spots_tabs.setProperty("liveRaidSpotsTabs", True)

        # Page 1: the full roster/assignment view stays readable at raid speed.
        roster_tab = QWidget()
        roster_layout = QVBoxLayout(roster_tab)
        roster_layout.setContentsMargins(0, 0, 0, 0)
        roster_layout.setSpacing(6)

        self.spots_table = QTableWidget(0, 8)
        self.spots_table.setProperty("liveRaidRosterTable", True)
        self.spots_table.setHorizontalHeaderLabels(
            ("Spot", "Player", "Assignment", "Status", "Ult", "Notes", "Alive", "Evidence")
        )
        self.spots_table.verticalHeader().setVisible(False)
        self.spots_table.horizontalHeader().setStretchLastSection(True)
        self.spots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.spots_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.spots_table.setAlternatingRowColors(False)
        self.spots_table.setShowGrid(False)
        roster_layout.addWidget(self.spots_table)

        roster_actions = QHBoxLayout()
        roster_actions.setContentsMargins(0, 0, 0, 0)
        roster_actions.setSpacing(6)

        view_assignments = QPushButton("Assignments")
        view_assignments.setProperty("liveRaidSecondaryAction", True)
        view_assignments.clicked.connect(lambda: self.pageRequested.emit("assignments"))
        roster_actions.addWidget(view_assignments, 1)
        roster_actions.addStretch(1)
        roster_layout.addLayout(roster_actions)

        self.raid_spots_tabs.addTab(roster_tab, "Names & Assignments")

        # Page 2: give the Raid Plan map the full card width instead of squeezing
        # raid-critical positioning into a side panel.
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(6)

        self.inline_raid_map = QLabel(
            "No Raid Plan map linked for this encounter."
        )
        self.inline_raid_map.setProperty("positioningMap", True)
        self.inline_raid_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inline_raid_map.setWordWrap(True)
        self.inline_raid_map.setMinimumHeight(420)
        self.inline_raid_map.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )

        self.raid_map_scroll = QScrollArea()
        self.raid_map_scroll.setWidgetResizable(False)
        self.raid_map_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.raid_map_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.raid_map_scroll.setWidget(self.inline_raid_map)
        map_layout.addWidget(self.raid_map_scroll, 1)

        map_actions = QHBoxLayout()
        map_actions.setContentsMargins(0, 0, 0, 0)
        map_actions.setSpacing(6)

        fit_map = QPushButton("Fit")
        fit_map.setToolTip("Fit the full Raid Map in the Live Raid card")
        fit_map.clicked.connect(self._fit_raid_map)
        map_actions.addWidget(fit_map)

        open_full = QPushButton("Open Full Map")
        open_full.setToolTip("Open the current Raid Map in a large zoomable window.")
        open_full.clicked.connect(self._open_raid_map_popup)
        map_actions.addWidget(open_full)

        map_actions.addStretch(1)

        self.raid_map_button = QPushButton("Raid Map ▾")
        self.raid_map_button.setProperty("liveRaidSecondaryAction", True)
        self.raid_map_button.clicked.connect(self._show_raid_map_menu)
        map_actions.addWidget(self.raid_map_button)
        map_layout.addLayout(map_actions)

        self.raid_spots_tabs.addTab(map_tab, "Raid Map")
        spots.addWidget(self.raid_spots_tabs)
        middle.addWidget(spots, 5)

        callouts = self._style_live_card(FoundryCard("Current Callouts", "warning"), "callouts")
        self.callouts_host = QWidget()
        self.callouts_host.setProperty("liveRaidCalloutList", True)
        self.callouts_layout = QVBoxLayout(self.callouts_host)
        self.callouts_layout.setContentsMargins(0, 0, 0, 0)
        self.callouts_layout.setSpacing(0)
        callouts.addWidget(self.callouts_host)
        middle.addWidget(callouts, 3)
        middle.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.workspace_layout.addLayout(middle)

        lower = QHBoxLayout()
        lower.setSpacing(10)

        timeline = self._style_live_card(
            FoundryCard("Next 60 Seconds", "stopwatch"), "timeline"
        )
        timeline.setMinimumHeight(220)
        self.timeline_text = QLabel(
            "Select an encounter to load reviewed timing and threshold context."
        )
        self.timeline_text.setProperty("liveRaidTimelineText", True)
        self.timeline_text.setWordWrap(True)
        self.timeline_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        timeline.addWidget(self.timeline_text)
        timeline.addStretch(1)
        lower.addWidget(timeline, 3)

        notes = self._style_live_card(
            FoundryCard("Quick Notes / Run Sheet", "clipboard"), "notes"
        )
        notes.setProperty("foundryNoteCard", True)
        notes.setMinimumHeight(220)
        self.encounter_checklist_label = QLabel("No encounter checklist loaded.")
        self.encounter_checklist_label.setProperty("liveRaidChecklistText", True)
        self.encounter_checklist_label.setWordWrap(True)
        notes.addWidget(self.encounter_checklist_label)

        self.run_notes_edit = QTextEdit()
        self.run_notes_edit.setProperty("parchmentEditor", True)
        self.run_notes_edit.setProperty("liveRaidNotesEditor", True)
        self.run_notes_edit.setAcceptRichText(False)
        self.run_notes_edit.setPlaceholderText("Add manual pull notes, reminders, or observations…")
        self.run_notes_edit.setMinimumHeight(120)
        notes.addWidget(self.run_notes_edit)
        self.save_run_notes_button = QPushButton("Save Run Notes")
        self.save_run_notes_button.setProperty("liveRaidNoteAction", True)
        self.save_run_notes_button.clicked.connect(self._save_run_notes)
        notes.addWidget(self.save_run_notes_button)
        lower.addWidget(notes, 4)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(10)

        coverage = self._style_live_card(
            FoundryCard("Coverage Snapshot", "shield"), "coverage"
        )
        self.coverage_label = QLabel(
            "NEEDS REVIEW\nOpen Coverage for authoritative provider evidence."
        )
        self.coverage_label.setProperty("liveRaidCoverageText", True)
        self.coverage_label.setWordWrap(True)
        coverage.addWidget(self.coverage_label)
        open_coverage = QPushButton("Open Coverage")
        open_coverage.setProperty("liveRaidSecondaryAction", True)
        open_coverage.clicked.connect(lambda: self.pageRequested.emit("console:7"))
        coverage.addWidget(open_coverage)
        right_column.addWidget(coverage, 1)

        recent = self._style_live_card(
            FoundryCard("Recent Events", "archive"), "recent"
        )
        self.events_label = QLabel("No manual run events yet.")
        self.events_label.setProperty("liveRaidEventText", True)
        self.events_label.setWordWrap(True)
        self.events_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        recent.addWidget(self.events_label)
        recent.addStretch(1)
        right_column.addWidget(recent, 1)

        lower.addLayout(right_column, 3)
        self.workspace_layout.addLayout(lower, 1)

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
        current_id = str(getattr(self._plan, "plan_id", "") or "").strip()
        target_id = str(plan_id or "").strip() if isinstance(plan_id, str) else ""
        if (
            current_id
            and target_id != current_id
            and self.has_pending_changes()
            and not confirm_unsaved_changes(
                self,
                self,
                action_text="switch Live Raid plans",
            )
        ):
            self.plan_combo.blockSignals(True)
            try:
                index = self.plan_combo.findData(current_id)
                if index >= 0:
                    self.plan_combo.setCurrentIndex(index)
            finally:
                self.plan_combo.blockSignals(False)
            return

        self._plan = self.repository.get(plan_id) if isinstance(plan_id, str) and plan_id else None
        self._refresh_encounters()
        self._render_plan()

    def has_pending_changes(self) -> bool:
        if self._plan is None or not hasattr(self, "run_notes_edit"):
            return False
        return self.run_notes_edit.toPlainText().strip() != self._run_notes_baseline

    def save_pending_changes(self) -> bool:
        if not self.has_pending_changes():
            return True
        self._save_run_notes()
        return not self.has_pending_changes()

    def discard_pending_changes(self) -> bool:
        if self._plan is None:
            self._run_notes_baseline = ""
            if hasattr(self, "run_notes_edit"):
                self.run_notes_edit.clear()
            return True
        saved = self.user_state.run_notes(self._plan.plan_id)
        self.run_notes_edit.setPlainText(saved)
        self._run_notes_baseline = self.run_notes_edit.toPlainText().strip()
        mark_saved(self, "Discarded")
        return True

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            nested = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif nested is not None:
                CityLiveRaidPage._clear_layout(nested)

    def _callout_row(
        self,
        *,
        marker: str,
        title: str,
        detail: str = "",
        badge: str = "",
        role: str = "planned",
    ) -> QWidget:
        row = QFrame()
        row.setProperty("liveRaidCalloutRow", True)
        row.setProperty("liveRaidCalloutRole", role)
        row.setStyleSheet(
            "QFrame[liveRaidCalloutRow=\"true\"] {"
            " border-bottom: 1px solid #26363A;"
            " background: transparent;"
            " }"
            "QLabel[liveRaidCalloutMarker=\"true\"] {"
            " color: #BFC8C6;"
            " font-family: 'Montserrat';"
            " font-size: 11px;"
            " }"
            "QLabel[liveRaidCalloutTitle=\"true\"] {"
            " color: #E5ECEB;"
            " font-family: 'Montserrat';"
            " font-size: 13px;"
            " font-weight: 600;"
            " }"
            "QLabel[liveRaidCalloutDetail=\"true\"] {"
            " color: #BFC8C6;"
            " font-family: 'Montserrat';"
            " font-size: 11px;"
            " }"
            "QLabel[liveRaidCalloutBadge=\"true\"] {"
            " color: #C8A46A;"
            " border: 1px solid #6F5B37;"
            " border-radius: 4px;"
            " padding: 2px 6px;"
            " font-family: 'Montserrat';"
            " font-size: 10px;"
            " font-weight: 600;"
            " }"
        )
        layout = QGridLayout(row)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(1)

        marker_label = QLabel(marker)
        marker_label.setProperty("liveRaidCalloutMarker", True)
        marker_label.setProperty("liveRaidCalloutRole", role)
        marker_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        marker_label.setMinimumWidth(58)
        marker_label.setMaximumWidth(72)
        layout.addWidget(marker_label, 0, 0, 2, 1)

        title_label = QLabel(title or "Callout")
        title_label.setProperty("liveRaidCalloutTitle", True)
        title_label.setWordWrap(True)
        layout.addWidget(title_label, 0, 1)

        if badge:
            badge_label = QLabel(badge)
            badge_label.setProperty("liveRaidCalloutBadge", True)
            badge_label.setProperty("liveRaidCalloutRole", role)
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_label.setMinimumWidth(56)
            layout.addWidget(badge_label, 0, 2)

        if detail:
            detail_label = QLabel(detail)
            detail_label.setProperty("liveRaidCalloutDetail", True)
            detail_label.setWordWrap(True)
            layout.addWidget(detail_label, 1, 1, 1, 2)

        layout.setColumnStretch(1, 1)
        return row

    def _render_callout_rows(
        self,
        rows: list[tuple[str, str, str, str, str]],
    ) -> None:
        self._clear_layout(self.callouts_layout)
        if not rows:
            empty = QLabel("No reviewed encounter callouts or plan responsibilities are available.")
            empty.setProperty("liveRaidCalloutEmpty", True)
            empty.setWordWrap(True)
            self.callouts_layout.addWidget(empty)
            return
        for marker, title, detail, badge, role in rows[:8]:
            self.callouts_layout.addWidget(
                self._callout_row(
                    marker=marker,
                    title=title,
                    detail=detail,
                    badge=badge,
                    role=role,
                )
            )

    def _current_linked_raid_map_id(self) -> str:
        if self._plan is None:
            return ""
        encounter_id = _clean(self.encounter_combo.currentData())
        if not encounter_id:
            return ""
        return self.user_state.linked_raid_map_id(self._plan.plan_id, encounter_id)

    def _current_linked_raid_map(self):
        encounter_id = _clean(self.encounter_combo.currentData())
        map_id = self._current_linked_raid_map_id()
        if not encounter_id or not map_id:
            return None
        try:
            return next(
                (
                    row
                    for row in self.raid_map_store.list_maps(encounter_id)
                    if row.map_id == map_id
                ),
                None,
            )
        except (OSError, RuntimeError, ValueError):
            return None

    def _apply_raid_map_zoom(self) -> None:
        pixmap = self._raid_map_source_pixmap
        if pixmap.isNull():
            return
        scale = max(0.5, min(3.0, float(self._raid_map_zoom)))
        width = max(1, int(round(pixmap.width() * scale)))
        height = max(1, int(round(pixmap.height() * scale)))
        rendered = pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.inline_raid_map.setText("")
        self.inline_raid_map.setPixmap(rendered)
        self.inline_raid_map.resize(rendered.size())

    def _change_raid_map_zoom(self, delta: float) -> None:
        if self._raid_map_source_pixmap.isNull():
            return
        self._raid_map_zoom = max(
            0.5,
            min(3.0, float(self._raid_map_zoom) + float(delta)),
        )
        self._apply_raid_map_zoom()

    def _fit_raid_map(self) -> None:
        pixmap = self._raid_map_source_pixmap
        if pixmap.isNull() or not hasattr(self, "raid_map_scroll"):
            return
        viewport = self.raid_map_scroll.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        width_scale = viewport.width() / max(1, pixmap.width())
        height_scale = viewport.height() / max(1, pixmap.height())
        self._raid_map_zoom = max(0.5, min(3.0, min(width_scale, height_scale)))
        self._apply_raid_map_zoom()

    def _refresh_inline_raid_map(self) -> None:
        if not hasattr(self, "inline_raid_map"):
            return
        record = self._current_linked_raid_map()
        if record is None:
            self._raid_map_source_pixmap = QPixmap()
            self.inline_raid_map.setPixmap(QPixmap())
            self.inline_raid_map.setText(
                "No Raid Plan map linked for this encounter."
            )
            self.inline_raid_map.adjustSize()
            return

        path = self.raid_map_store.resolve_path(record)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._raid_map_source_pixmap = QPixmap()
            self.inline_raid_map.setPixmap(QPixmap())
            self.inline_raid_map.setText(
                "Linked Raid Plan map could not be displayed."
            )
            self.inline_raid_map.adjustSize()
            return

        self._raid_map_source_pixmap = pixmap
        self._raid_map_zoom = 1.0
        QTimer.singleShot(0, self._fit_raid_map)

    def _open_raid_map_popup(self) -> None:
        pixmap = self._raid_map_source_pixmap
        if pixmap.isNull():
            self.status.warning("No linked Raid Map is available to enlarge.")
            return

        dialog = QDialog(self)
        encounter_name = (
            self.encounter_combo.currentText().removeprefix("Encounter: ").strip()
            or "Raid Map"
        )
        dialog.setWindowTitle(f"Raid Map • {encounter_name}")
        dialog.resize(1280, 820)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        map_label = QLabel()
        map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(map_label)
        root.addWidget(scroll, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        zoom_state = {"value": 1.0}

        def render() -> None:
            scale = max(0.5, min(4.0, float(zoom_state["value"])))
            rendered = pixmap.scaled(
                max(1, int(round(pixmap.width() * scale))),
                max(1, int(round(pixmap.height() * scale))),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            map_label.setPixmap(rendered)
            map_label.resize(rendered.size())

        def zoom_by(delta: float) -> None:
            zoom_state["value"] = max(
                0.5,
                min(4.0, float(zoom_state["value"]) + float(delta)),
            )
            render()

        def fit() -> None:
            viewport = scroll.viewport().size()
            if viewport.width() <= 0 or viewport.height() <= 0:
                return
            zoom_state["value"] = max(
                0.5,
                min(
                    4.0,
                    min(
                        viewport.width() / max(1, pixmap.width()),
                        viewport.height() / max(1, pixmap.height()),
                    ),
                ),
            )
            render()

        zoom_out = QPushButton("−")
        zoom_out.setToolTip("Zoom out")
        zoom_out.clicked.connect(lambda: zoom_by(-0.25))
        controls.addWidget(zoom_out)

        fit_button = QPushButton("Fit")
        fit_button.clicked.connect(fit)
        controls.addWidget(fit_button)

        zoom_in = QPushButton("+")
        zoom_in.setToolTip("Zoom in")
        zoom_in.clicked.connect(lambda: zoom_by(0.25))
        controls.addWidget(zoom_in)

        controls.addStretch(1)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        controls.addWidget(close_button)

        root.addLayout(controls)
        QTimer.singleShot(0, fit)
        dialog.exec()

    def _show_raid_map_menu(self) -> None:
        menu = QMenu(self)
        encounter_id = _clean(self.encounter_combo.currentData())
        linked_map_id = self._current_linked_raid_map_id()

        open_action = menu.addAction("Open Linked Raid Map")
        open_action.setEnabled(bool(encounter_id and linked_map_id))
        open_action.triggered.connect(self._open_linked_raid_map)

        link_action = menu.addAction(
            "Change Raid Map…" if linked_map_id else "Link Raid Map…"
        )
        link_action.setEnabled(bool(encounter_id))
        link_action.triggered.connect(self._link_raid_map)

        clear_action = menu.addAction("Clear Raid Map Link")
        clear_action.setEnabled(bool(linked_map_id))
        clear_action.triggered.connect(self._clear_raid_map_link)

        if not encounter_id:
            menu.addSeparator()
            note = menu.addAction("Select an encounter first")
            note.setEnabled(False)

        menu.exec(self.raid_map_button.mapToGlobal(self.raid_map_button.rect().bottomLeft()))

    def _link_raid_map(self) -> None:
        if self._plan is None:
            return
        encounter_id = _clean(self.encounter_combo.currentData())
        if not encounter_id:
            self.status.warning("Select an encounter before linking a Raid Map.")
            return
        maps = self.raid_map_store.list_maps(encounter_id)
        if not maps:
            self.status.warning(
                "No Raid Maps are saved for this encounter yet. Add one from Mechanics first."
            )
            return

        labels = [row.label for row in maps]
        current_map_id = self._current_linked_raid_map_id()
        current_index = next(
            (index for index, row in enumerate(maps) if row.map_id == current_map_id),
            0,
        )
        selected, ok = QInputDialog.getItem(
            self,
            "Link Raid Map",
            "Raid Map for this Live Plan encounter:",
            labels,
            current_index,
            False,
        )
        if not ok:
            return
        index = labels.index(selected)
        record = maps[index]
        if (
            current_map_id
            and record.map_id != current_map_id
            and not confirm_replacement(
                self,
                title="Change Raid Map Link",
                object_label=f'Use "{record.label}" for this encounter instead?',
                impact=(
                    "The current Raid Map link will be replaced. Both saved maps remain "
                    "available in Encounters."
                ),
                confirm_text="Change Link",
            )
        ):
            return
        self.user_state.set_linked_raid_map_id(
            self._plan.plan_id,
            encounter_id,
            record.map_id,
        )
        self.raid_map_button.setText(f"Raid Map: {record.label} ▾")
        self._render_encounter_context()
        self._refresh_inline_raid_map()
        self._refresh_events()
        self.status.success(
            f"Linked {record.label} to {self._plan.name} • {self.encounter_combo.currentText()}."
        )

    def _clear_raid_map_link(self) -> None:
        if self._plan is None:
            return
        encounter_id = _clean(self.encounter_combo.currentData())
        if not encounter_id:
            return
        record = self._current_linked_raid_map()
        label = record.label if record is not None else "the linked Raid Map"
        if not confirm_destructive_action(
            self,
            title="Clear Raid Map Link",
            object_label=f'Clear "{label}" from this Live Raid encounter?',
            impact=(
                "This removes only the link from this Raid Plan encounter. "
                "The saved Raid Map itself is not deleted."
            ),
            confirm_text="Clear Link",
        ):
            return
        self.user_state.set_linked_raid_map_id(
            self._plan.plan_id,
            encounter_id,
            "",
        )
        self.raid_map_button.setText("Raid Map ▾")
        self._render_encounter_context()
        self._refresh_inline_raid_map()
        self._refresh_events()
        self.status.info("Raid Map link cleared for this Live Plan encounter.")

    def _open_linked_raid_map(self) -> None:
        encounter_id = _clean(self.encounter_combo.currentData())
        map_id = self._current_linked_raid_map_id()
        if not encounter_id or not map_id:
            self.status.warning("Link a Raid Map to this encounter first.")
            return
        self.raidMapRequested.emit(encounter_id, map_id)

    def _refresh_raid_map_button(self) -> None:
        if not hasattr(self, "raid_map_button"):
            return
        encounter_id = _clean(self.encounter_combo.currentData())
        if self._plan is None or not encounter_id:
            self.raid_map_button.setText("Raid Map ▾")
            self.raid_map_button.setEnabled(bool(self._plan is not None))
            return
        map_id = self._current_linked_raid_map_id()
        record = self._current_linked_raid_map()
        self.raid_map_button.setText(
            f"Raid Map: {record.label} ▾" if record is not None else "Raid Map ▾"
        )
        self.raid_map_button.setEnabled(True)

    def _refresh_encounters(self) -> None:
        self.encounter_combo.blockSignals(True)
        self.encounter_combo.clear()
        self.encounter_combo.addItem("Encounter: Trial / General", "")
        plan = self._plan
        if plan is not None:
            try:
                rows = self.encounter_projection.encounters_for_trial(plan.trial_id)
            except Exception:
                rows = ()
            for row in rows:
                self.encounter_combo.addItem(f"Encounter: {row.name}", row.encounter_id)

            remembered = self.user_state.selected_encounter_id(plan.plan_id)
            if remembered:
                index = self.encounter_combo.findData(remembered)
                if index >= 0:
                    self.encounter_combo.setCurrentIndex(index)
        self.encounter_combo.blockSignals(False)
        self._load_encounter_context()
        self._refresh_raid_map_button()
        self._refresh_inline_raid_map()
        self.boss_mechanics_button.setEnabled(
            bool(self._plan is not None and _clean(self.encounter_combo.currentData()))
        )

    def _encounter_changed(self, *_args) -> None:
        if self._plan is not None:
            self.user_state.set_selected_encounter_id(
                self._plan.plan_id,
                _clean(self.encounter_combo.currentData()),
            )
        self._load_encounter_context()
        self._refresh_raid_map_button()
        self._refresh_inline_raid_map()
        self.boss_mechanics_button.setEnabled(
            bool(self._plan is not None and _clean(self.encounter_combo.currentData()))
        )
        self._render_encounter_context()

    def _open_boss_mechanics(self) -> None:
        encounter_id = _clean(self.encounter_combo.currentData())
        if not encounter_id:
            self.status.warning("Select an encounter before opening Boss Mechanics.")
            return
        self.bossMechanicsRequested.emit(encounter_id)

    def _load_encounter_context(self) -> None:
        self._encounter_context = None
        plan = self._plan
        encounter_id = _clean(self.encounter_combo.currentData())
        if plan is None or not encounter_id:
            return
        try:
            self._encounter_context = self.encounter_projection.context_for(
                plan,
                encounter_id,
            )
        except Exception as exc:
            self.status.warning(f"Encounter context could not be loaded: {exc}")

    def _elapsed_pull_seconds(self) -> int | None:
        if self._plan is None:
            return None
        state = self.user_state.run_state(self._plan.plan_id)
        if not state.get("active"):
            return None
        started = _parse_iso(state.get("started_at"))
        if started is None:
            return None
        return max(0, int((datetime.now(timezone.utc) - started).total_seconds()))

    @staticmethod
    def _clock_marker(seconds: float) -> str:
        whole = max(0, int(round(seconds)))
        minutes, second = divmod(whole, 60)
        return f"{minutes}:{second:02d}"

    def _render_encounter_context(self) -> None:
        plan = self._plan
        context = self._encounter_context
        if plan is None:
            return
        if context is None:
            self.hero_title.setText(
                f"{plan.name}\n{plan.trial_id} · {plan.difficulty or 'Difficulty not set'}"
            )
            self.phase_label.setText("Phase Guide\nTrial / General")
            self.timeline_text.setText(
                "Select an encounter to load reviewed boss timing and phase context."
            )
            self.encounter_checklist_label.setText(
                "Trial / General notes. No boss-specific checklist is selected."
            )
            return

        self.hero_title.setText(
            f"{context.encounter_name}\n"
            f"{context.content_name or plan.trial_id} · {plan.difficulty or 'Difficulty not set'}"
        )
        phase_lines = [
            "Phase Guide",
            context.phase_lines[0] if context.phase_lines else "No reviewed phase markers",
        ]
        if self._current_linked_raid_map() is not None:
            phase_lines.append("Map Available")
        self.phase_label.setText("\n".join(phase_lines))

        elapsed = self._elapsed_pull_seconds()
        window_start = 0 if elapsed is None else elapsed
        window_end = window_start + 60
        upcoming = [
            event
            for event in context.clock_events
            if event.start_seconds >= window_start
            and event.start_seconds <= window_end
        ]
        if upcoming:
            lines = []
            for event in upcoming[:8]:
                marker = self._clock_marker(event.start_seconds)
                if elapsed is not None:
                    remaining = max(0, int(round(event.start_seconds - elapsed)))
                    prefix = f"in {remaining}s"
                else:
                    prefix = f"at {marker}"
                detail = f" — {event.detail}" if event.detail else ""
                lines.append(f"{prefix}: {event.label}{detail}")
            self.timeline_text.setText("\n".join(lines))
        elif context.clock_events:
            self.timeline_text.setText(
                "No reviewed clock-backed encounter events fall in the next 60 seconds."
            )
        elif context.phase_lines:
            self.timeline_text.setText(
                "No reviewed wall-clock events are persisted for this encounter. "
                "Threshold guide: " + " | ".join(context.phase_lines[:4])
            )
        else:
            self.timeline_text.setText(
                "No reviewed wall-clock or phase timeline is persisted for this encounter."
            )

        callout_rows: list[tuple[str, str, str, str, str]] = []

        for condition in context.condition_events:
            marker = _clean(condition.marker) or "PLAN"
            role = "threshold" if "%" in marker else "planned"
            badge = "THRESHOLD" if role == "threshold" else "PLAN"
            callout_rows.append(
                (
                    marker,
                    condition.label,
                    condition.detail,
                    badge,
                    role,
                )
            )

        for line in context.callouts:
            callout_rows.append(("PLAN", line, "", "PLAN", "planned"))

        self._render_callout_rows(callout_rows)
        self.encounter_checklist_label.setText(
            "\n".join(f"□ {line}" for line in context.checklist)
            if context.checklist
            else "No reviewed encounter checklist items are available."
        )

    def _render_plan(self) -> None:
        plan = self._plan
        self.spots_table.setRowCount(0)
        if plan is None:
            self.hero_art.set_source(None)
            self.hero_title.setText("No Raid Plan selected")
            self.phase_label.setText("Current Phase\n—")
            self.alive_label.setText("Planned roster")
            self.timer_label.setText("00:00")
            self.attempt_label.setText("#0")
            self.combat_label.setText("Not in pull")
            self._render_callout_rows([])
            self.timeline_text.setText("Select a Raid Plan and encounter.")
            self.encounter_checklist_label.setText("No encounter checklist loaded.")
            self.events_label.setText("No manual run events yet.")
            self.run_notes_edit.clear()
            self._run_notes_baseline = ""
            self._raid_map_source_pixmap = QPixmap()
            self.inline_raid_map.setPixmap(QPixmap())
            self.inline_raid_map.setText("No Raid Plan map linked for this encounter.")
            self.run_notes_edit.setEnabled(False)
            self.save_run_notes_button.setEnabled(False)
            return
        self.hero_art.set_source(trial_banner_path(plan.trial_id, plan.name))
        if not self.run_notes_edit.hasFocus():
            self.run_notes_edit.setPlainText(self.user_state.run_notes(plan.plan_id))
            self._run_notes_baseline = self.run_notes_edit.toPlainText().strip()
        self.hero_title.setText(
            f"{plan.name}\n{plan.trial_id} · {plan.difficulty or 'Difficulty not set'}"
        )
        self.alive_label.setText(f"{len(plan.members)} planned")
        self.phase_label.setText("Current Phase\nPlanned encounter context")
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

        plan_callouts = []
        for item in plan.triggered_responsibilities:
            plan_callouts.append(
                (
                    "PLAN",
                    _clean(item.directive) or item.trigger_key,
                    f"{item.seat_id} • {item.trigger_key}",
                    "PLAN",
                    "planned",
                )
            )
        self._render_callout_rows(plan_callouts)
        self._render_encounter_context()
        self._refresh_inline_raid_map()
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
        self.attempt_label.setText(f"#{attempt}")
        self.combat_label.setText("Pull active" if active else "Not in pull")
        self.pause_button.setText("Resume Notes" if paused else "Pause Notes")
        self.start_button.setEnabled(not active)
        self.end_button.setEnabled(active)
        self.run_notes_edit.setEnabled(not paused)
        self.save_run_notes_button.setEnabled(not paused)
        self._refresh_clock()

    def _refresh_clock(self) -> None:
        if self._plan is None:
            self.timer_label.setText("00:00")
            return
        state = self.user_state.run_state(self._plan.plan_id)
        if not state.get("active"):
            self.timer_label.setText("MANUAL\nPull 00:00")
            return
        started = _parse_iso(state.get("started_at"))
        if started is None:
            self.timer_label.setText("--:--")
            return
        seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
        minutes, second = divmod(seconds, 60)
        self.timer_label.setText(f"{minutes:02d}:{second:02d}")
        self._render_encounter_context()

    def _encounter_label(self, encounter_id: str) -> str:
        wanted = _clean(encounter_id)
        if not wanted:
            return "Trial / General"
        for index in range(self.encounter_combo.count()):
            if _clean(self.encounter_combo.itemData(index)) == wanted:
                text = _clean(self.encounter_combo.itemText(index))
                return text.removeprefix("Encounter: ").strip() or wanted
        return wanted

    @staticmethod
    def _duration_label(seconds: int | None) -> str:
        if seconds is None:
            return "active"
        minutes, second = divmod(max(0, int(seconds)), 60)
        return f"{minutes:02d}:{second:02d}"

    def _refresh_events(self) -> None:
        if self._plan is None:
            return
        attempts = self.user_state.attempt_history(self._plan.plan_id)[:4]
        attempt_lines = [
            (
                f"ATTEMPT #{row.attempt} • {self._encounter_label(row.encounter_id)} • "
                f"{self._duration_label(row.duration_seconds)}"
            )
            for row in attempts
        ]
        rows = self.user_state.events(self._plan.plan_id, limit=5)
        event_lines = [f"{event.evidence}  {event.text}" for event in rows]

        map_lines = []
        linked_map = self._current_linked_raid_map()
        if linked_map is not None:
            encounter_id = _clean(self.encounter_combo.currentData())
            map_lines.append(
                f"MAP  {self._encounter_label(encounter_id)} • {linked_map.label}"
            )

        lines = map_lines + attempt_lines + event_lines
        self.events_label.setText("\n".join(lines) or "No manual run events yet.")

    def _save_run_notes(self) -> None:
        if self._plan is None:
            self.status.warning("Select a Raid Plan before saving run notes.")
            return
        notes = self.run_notes_edit.toPlainText().strip()
        mark_saving(self)
        try:
            state = self.user_state.set_run_notes(self._plan.plan_id, notes)
        except Exception as exc:
            mark_save_failed(self, str(exc))
            self.status.error(f"Run notes could not be saved: {exc}")
            return
        attempt = int(state.get("attempt", 0) or 0)
        archived = self.user_state.save_review_note(
            plan_id=self._plan.plan_id,
            trial_id=self._plan.trial_id,
            plan_name=self._plan.name,
            attempt=attempt,
            notes=notes,
            started_at=_clean(state.get("started_at")),
            ended_at=_clean(state.get("ended_at")),
            encounter_id=_clean(state.get("encounter_id")),
        )
        if archived is None:
            self.status.info("Blank notes cleared from the active Raid Plan.")
        else:
            label = f"attempt #{attempt}" if attempt else "general note"
            self.status.info(f"Run notes saved to Review for {label}.")
        self._run_notes_baseline = notes
        mark_saved(self)
        self._refresh_events()

    def _start_pull(self) -> None:
        if self._plan is None:
            self.status.warning("Select a Raid Plan before starting a pull.")
            return
        self.user_state.start_pull(
            self._plan.plan_id,
            encounter_id=_clean(self.encounter_combo.currentData()),
            trial_id=self._plan.trial_id,
            plan_name=self._plan.name,
        )
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
