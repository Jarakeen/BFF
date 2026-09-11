from __future__ import annotations

"""Populate the Encounters planning page from reviewed encounter evidence.

The Encounters page originally displayed illustrative phase/mechanic placeholders.
This support layer keeps the planning/positioning UI intact while replacing those
examples with selected-boss timeline and strategy projections. Canonical boss-guide
phases remain authoritative; reviewed evidence fills only missing timeline structure.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False


def _projection_service(self) -> EncounterGuideEvidenceProjectionService:
    service = getattr(self, "_encounter_guide_projection_service", None)
    if service is None:
        service = EncounterGuideEvidenceProjectionService(Path(self.guide_service.database).parent)
        self._encounter_guide_projection_service = service
    return service


def _sync_event_lists(self, row: int, *, source: str) -> None:
    if row < 0:
        return
    other = self.encounter_timeline_list if source == "phase" else self.encounter_phase_list
    if other.currentRow() != row:
        other.blockSignals(True)
        other.setCurrentRow(row)
        other.blockSignals(False)
    _render_selected_event(self, row)


def _assignments_tab_with_evidence(self) -> QWidget:
    tab = QWidget()
    root = QVBoxLayout(tab)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(8)

    upper = QHBoxLayout()
    upper.setSpacing(8)

    left = QVBoxLayout()
    left.setSpacing(8)

    controls = FoundryCard("Select Boss", "boss")
    boss_row = QHBoxLayout()
    self.boss_combo = QComboBox()
    boss_row.addWidget(self.boss_combo, 1)
    self.previous_boss_button = QPushButton("‹")
    self.next_boss_button = QPushButton("›")
    boss_row.addWidget(self.previous_boss_button)
    boss_row.addWidget(self.next_boss_button)
    controls.addLayout(boss_row)

    phase_row = QHBoxLayout()
    self.encounter_phase_list = QListWidget()
    self.encounter_phase_list.setMaximumWidth(220)
    phase_row.addWidget(self.encounter_phase_list)

    self.positioning_card = FoundryCard("Positioning", "treasure-map").set_watermark("compass", 0.035)
    self.positioning_preview = QLabel()
    self.positioning_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.positioning_preview.setMinimumHeight(300)
    self.positioning_preview.setProperty("positioningMap", True)
    self.positioning_preview.setText(
        "No positioning capture yet.\n\n"
        "Build the encounter on the Mechanics tab, then use Capture Positioning."
    )
    self.positioning_card.addWidget(self.positioning_preview)
    open_board = QPushButton("Open Mechanics Map")
    open_board.clicked.connect(lambda: self.section_tabs.setCurrentIndex(2))
    self.positioning_card.set_header_action(open_board)
    phase_row.addWidget(self.positioning_card, 1)
    controls.addLayout(phase_row)
    left.addWidget(controls, 3)

    assignments = FoundryCard("Player Assignments", "assignment")
    filter_row = QHBoxLayout()
    for text in ("All Players", "Tanks", "Healers", "DPS", "Special"):
        button = QPushButton(text)
        button.setCheckable(True)
        filter_row.addWidget(button)
    search = QLineEdit()
    search.setPlaceholderText("Search player or assignment…")
    filter_row.addWidget(search, 1)
    assignments.addLayout(filter_row)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(("Player", "Role", "Primary Assignment", "Secondary Assignment(s)", "Notes"))
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.setMinimumHeight(230)
    assignments.addWidget(table)
    left.addWidget(assignments, 2)
    upper.addLayout(left, 6)

    middle = QVBoxLayout()
    middle.setSpacing(8)

    timeline = FoundryCard("Phase Timeline Overview", "stopwatch")
    self.encounter_timeline_list = QListWidget()
    timeline.addWidget(self.encounter_timeline_list)
    middle.addWidget(timeline, 3)

    event = FoundryCard("Event Details", "mechanics")
    self.encounter_event_detail = QLabel("Select a timeline event to inspect its reviewed details.")
    self.encounter_event_detail.setWordWrap(True)
    self.encounter_phase_list.currentRowChanged.connect(
        lambda row: _sync_event_lists(self, row, source="phase")
    )
    self.encounter_timeline_list.currentRowChanged.connect(
        lambda row: _sync_event_lists(self, row, source="timeline")
    )
    event.addWidget(self.encounter_event_detail)
    event.addWidget(QPushButton("Add Custom Event"))
    middle.addWidget(event, 2)
    upper.addLayout(middle, 3)

    right = QVBoxLayout()
    right.setSpacing(8)

    mechanics = FoundryCard("Mechanics Reference", "open-book")
    self.encounter_mechanic_search = QLineEdit()
    self.encounter_mechanic_search.setPlaceholderText("Search mechanics…")
    self.encounter_mechanic_search.textChanged.connect(lambda _text: _filter_mechanics(self))
    mechanics.addWidget(self.encounter_mechanic_search)
    self.encounter_mechanic_list = QListWidget()
    self.encounter_mechanic_list.currentRowChanged.connect(lambda _row: _render_selected_mechanic(self))
    mechanics.addWidget(self.encounter_mechanic_list)
    right.addWidget(mechanics, 2)

    detail = FoundryCard("Mechanic Details", "crossed-swords")
    self.encounter_mechanic_detail = QLabel("Select a mechanic to show behavior and handling.")
    self.encounter_mechanic_detail.setWordWrap(True)
    detail.addWidget(self.encounter_mechanic_detail)
    right.addWidget(detail, 3)

    notes = FoundryCard("Quick Notes", "feather").make_parchment().set_watermark("feather", 0.12)
    self.encounter_quick_notes = QLabel("No reviewed raid-lead callouts for the selected encounter yet.")
    self.encounter_quick_notes.setWordWrap(True)
    notes.addWidget(self.encounter_quick_notes)
    notes.set_header_action(QPushButton("Add Note"))
    right.addWidget(notes, 2)

    upper.addLayout(right, 3)
    root.addLayout(upper, 1)
    return tab


def _timeline_rows(self, guide, projection):
    if guide.phases:
        return tuple(
            (phase.threshold or "?", phase.label or "Phase", phase.description or "Canonical encounter phase.")
            for phase in guide.phases
        )
    return tuple((row.marker, row.label, row.detail) for row in projection.timeline)


def _render_selected_event(self, row_index: int | None = None) -> None:
    rows = getattr(self, "_encounter_display_timeline", ())
    if row_index is None:
        row_index = self.encounter_timeline_list.currentRow() if hasattr(self, "encounter_timeline_list") else -1
    if row_index < 0 or row_index >= len(rows):
        self.encounter_event_detail.setText("Select a timeline event to inspect its reviewed details.")
        return
    marker, label, detail = rows[row_index]
    self.encounter_event_detail.setText(f"{marker} • {label}\n\n{detail}")


def _filter_mechanics(self) -> None:
    rows = getattr(self, "_encounter_strategy_rows", ())
    query = self.encounter_mechanic_search.text().strip().casefold()
    self.encounter_mechanic_list.blockSignals(True)
    self.encounter_mechanic_list.clear()
    self._encounter_visible_strategy_rows = []
    for row in rows:
        common = ", ".join(row.common_names)
        haystack = f"{row.mechanic} {common} {row.summary} {row.mitigation}".casefold()
        if query and query not in haystack:
            continue
        label = row.mechanic + (f" ({common})" if common else "")
        self.encounter_mechanic_list.addItem(label)
        self._encounter_visible_strategy_rows.append(row)
    self.encounter_mechanic_list.blockSignals(False)
    if self.encounter_mechanic_list.count():
        self.encounter_mechanic_list.setCurrentRow(0)
        _render_selected_mechanic(self)
    else:
        self.encounter_mechanic_detail.setText("No reviewed mechanics match the current search.")


def _render_selected_mechanic(self) -> None:
    rows = getattr(self, "_encounter_visible_strategy_rows", ())
    index = self.encounter_mechanic_list.currentRow() if hasattr(self, "encounter_mechanic_list") else -1
    if index < 0 or index >= len(rows):
        return
    row = rows[index]
    common = f"\nCommon names: {', '.join(row.common_names)}" if row.common_names else ""
    self.encounter_mechanic_detail.setText(
        f"{row.mechanic}{common}\n\n"
        f"WHAT IT DOES\n{row.summary}\n\n"
        f"HOW TO HANDLE IT\n{row.mitigation}"
    )


def _render_encounter_evidence(self, encounter_id: str, encounter_name: str) -> None:
    service = _projection_service(self)
    projection = service.get(encounter_id, encounter_name)
    guide = self.guide_service.get(encounter_id)
    timeline_rows = _timeline_rows(self, guide, projection)
    self._encounter_display_timeline = timeline_rows

    self.encounter_phase_list.blockSignals(True)
    self.encounter_timeline_list.blockSignals(True)
    self.encounter_phase_list.clear()
    self.encounter_timeline_list.clear()
    for marker, label, _detail in timeline_rows:
        self.encounter_phase_list.addItem(f"{marker}  {label}")
        self.encounter_timeline_list.addItem(f"{marker}   {label}")
    self.encounter_phase_list.blockSignals(False)
    self.encounter_timeline_list.blockSignals(False)
    if timeline_rows:
        self.encounter_phase_list.setCurrentRow(0)
        self.encounter_timeline_list.setCurrentRow(0)
        _render_selected_event(self, 0)
    else:
        self.encounter_phase_list.addItem("No reviewed timeline yet")
        self.encounter_timeline_list.addItem("No reviewed timeline yet")
        self.encounter_event_detail.setText(
            "No canonical phase timeline or reviewed evidence fallback is available for this boss yet."
        )

    self._encounter_strategy_rows = projection.strategy
    _filter_mechanics(self)
    self.encounter_quick_notes.setText(
        "\n".join(f"• {value}" for value in projection.callouts)
        if projection.callouts
        else "No reviewed raid-lead callouts for the selected encounter yet."
    )

    if hasattr(self, "status"):
        timeline_source = "canonical" if guide.phases else "reviewed evidence fallback"
        self.status.success(
            f"Selected boss: {encounter_name}. Timeline {len(timeline_rows)} row(s) from {timeline_source}; "
            f"{len(projection.strategy)} reviewed mechanic strategy row(s)."
        )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.encounters_page import EncountersPage

    original_boss_changed = EncountersPage._boss_changed
    EncountersPage._assignments_tab = _assignments_tab_with_evidence

    def boss_changed_with_evidence(self, index: int) -> None:
        original_boss_changed(self, index)
        if index < 0 or index >= len(self._guide_summaries):
            return
        row = self._guide_summaries[index]
        _render_encounter_evidence(self, row.encounter_id, row.name)

    EncountersPage._boss_changed = boss_changed_with_evidence
    _INSTALLED = True
