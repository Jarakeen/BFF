from __future__ import annotations

"""Boss Guide page variant that renders reviewed runtime strategy observations.

The base MechanicsPage remains responsible for canonical/structural encounter data.
This subclass adds presentation-only runtime strategy surfaces fed by
EncounterRuntimeGuideProjectionService. Runtime observations remain explicitly
separate from canonical mechanics and persisted encounter_strategy rows.
"""

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.encounter_boss_guide import EncounterBossGuideService
from services.encounter_runtime_guide_projection_service import (
    EncounterGuideRuntimeProjection,
    EncounterRuntimeGuideProjectionService,
)
from services.expedition_service import ExpeditionService
from ui.components.foundry_card import FoundryCard
from ui.mechanics_page import MechanicsPage


_STRATEGY_PLACEHOLDER = (
    "Strategy remains separate from structural boss data. Reviewed handling will appear here "
    "when canonical strategy evidence is available."
)
_CALLOUT_PLACEHOLDER = (
    "Reviewed callouts will appear here when encounter handling data is explicitly available."
)
_REMINDER_PLACEHOLDER = (
    "Player reminders stay unresolved until reviewed encounter handling is available."
)
_RUNTIME_EVIDENCE_PLACEHOLDER = "No reviewed runtime observations are available for this encounter."

_RUNTIME_NOTE_PRIORITY = {
    "flight_2_primary_sustained_pressure": 0,
    "later_flights_interrupt_activity": 1,
    "flight_3_higher_death_incidence": 2,
    "flight_1_lighter_pressure": 3,
    "flight_windows_remain_active_combat": 4,
}

_RUNTIME_NOTE_GLANCE = {
    "flight_1_lighter_pressure": "Flight 1: lighter pressure",
    "flight_2_primary_sustained_pressure": "Flight 2: highest sustained pressure",
    "flight_3_higher_death_incidence": "Flight 3: highest observed death incidence",
    "later_flights_interrupt_activity": "Flights 2–3: interrupts matter",
    "flight_windows_remain_active_combat": "Flights: active add combat, not raid downtime",
}


class RuntimeMechanicsPage(MechanicsPage):
    """Mechanics page with reviewed real-run notes layered onto guide presentation."""

    def __init__(
        self,
        expedition: ExpeditionService,
        guide_service: EncounterBossGuideService | None = None,
        runtime_guide_service: EncounterRuntimeGuideProjectionService | None = None,
        parent=None,
    ) -> None:
        self.runtime_guide_service = runtime_guide_service
        self._runtime_strategy_ready = False
        super().__init__(expedition=expedition, guide_service=guide_service, parent=parent)
        self._capture_runtime_glance_labels()
        self._reshape_right_rail()
        self._install_runtime_strategy_tab()
        self._runtime_strategy_ready = True

        encounter_id = self.boss_combo.currentData()
        if encounter_id and self.guide_service is not None:
            self._render_runtime_strategy(str(encounter_id))
        else:
            self._clear_runtime_strategy()

    def _capture_runtime_glance_labels(self) -> None:
        """Capture current base-page placeholders; later access revalidates widget lifetime."""
        labels = {}
        for label in self.findChildren(QLabel):
            try:
                labels[label.text()] = label
            except RuntimeError:
                continue
        self.runtime_strategy_overview_label = labels.get(_STRATEGY_PLACEHOLDER)
        self.runtime_callouts_label = labels.get(_CALLOUT_PLACEHOLDER)
        self.runtime_reminders_label = labels.get(_REMINDER_PLACEHOLDER)

    def _live_glance_label(self, attribute: str, placeholder: str) -> QLabel | None:
        """Return a live glance label, reacquiring it if Qt destroyed the old wrapper target.

        Mechanics support layers may rebuild parts of the page after this subclass has
        captured the original placeholder QLabel. PySide keeps the Python wrapper even
        after the underlying C++ object is deleted, so every access must fail closed and
        reacquire the current placeholder instead of raising libshiboken RuntimeError.
        """
        label = getattr(self, attribute, None)
        if label is not None:
            try:
                label.text()
                return label
            except RuntimeError:
                setattr(self, attribute, None)

        for candidate in self.findChildren(QLabel):
            try:
                if candidate.text() == placeholder:
                    setattr(self, attribute, candidate)
                    return candidate
            except RuntimeError:
                continue
        return None

    def _set_glance_text(self, attribute: str, placeholder: str, text: str) -> None:
        label = self._live_glance_label(attribute, placeholder)
        if label is None:
            return
        try:
            label.setText(text)
        except RuntimeError:
            setattr(self, attribute, None)

    def _reshape_right_rail(self) -> None:
        """Remove duplicate My Notes and place reviewed runtime evidence at rail bottom."""
        cards: dict[str, FoundryCard] = {}
        for card in self.findChildren(FoundryCard):
            try:
                cards[card.title_label.text()] = card
            except RuntimeError:
                continue

        history = cards.get("Historical Notes")
        if history is None:
            return
        rail = _layout_containing_widget(self.workspace_layout, history)
        if rail is None:
            return

        duplicate_notes = cards.get("My Notes")
        if duplicate_notes is not None:
            rail.removeWidget(duplicate_notes)
            duplicate_notes.setParent(None)
            duplicate_notes.deleteLater()

        runtime = FoundryCard("Reviewed Runtime Evidence", "⌁").make_parchment().set_watermark(
            "feather", 0.08
        )
        self.runtime_strategy_summary = QLabel(_RUNTIME_EVIDENCE_PLACEHOLDER)
        self.runtime_strategy_summary.setWordWrap(True)
        runtime.addWidget(self.runtime_strategy_summary)

        self.runtime_evidence_source_label = QLabel("No reviewed runtime source.")
        self.runtime_evidence_source_label.setWordWrap(True)
        self.runtime_evidence_source_label.setProperty("muted", True)
        runtime.addWidget(self.runtime_evidence_source_label)
        self.runtime_evidence_card = runtime
        rail.addWidget(runtime)

    def _install_runtime_strategy_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        notes = FoundryCard("Real-run Notes", "✎").set_watermark("compass", 0.04)
        self.runtime_notes_table = QTableWidget(0, 2)
        self.runtime_notes_table.setHorizontalHeaderLabels(("Observation", "Confidence"))
        self.runtime_notes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.runtime_notes_table.verticalHeader().setVisible(False)
        self.runtime_notes_table.setAlternatingRowColors(True)
        notes_header = self.runtime_notes_table.horizontalHeader()
        notes_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        notes_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        notes.addWidget(self.runtime_notes_table)
        layout.addWidget(notes, 3)

        guidance = FoundryCard("Role Guidance", "⚑").set_watermark("compass", 0.04)
        self.runtime_guidance_table = QTableWidget(0, 3)
        self.runtime_guidance_table.setHorizontalHeaderLabels(("Role", "Priority", "Guidance"))
        self.runtime_guidance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.runtime_guidance_table.verticalHeader().setVisible(False)
        self.runtime_guidance_table.setAlternatingRowColors(True)
        guidance_header = self.runtime_guidance_table.horizontalHeader()
        guidance_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        guidance_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        guidance_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        guidance.addWidget(self.runtime_guidance_table)
        layout.addWidget(guidance, 3)

        index = next(
            (i for i in range(self.tabs.count()) if self.tabs.tabText(i) == "STRATEGY"),
            2,
        )
        self.tabs.removeTab(index)
        self.tabs.insertTab(index, tab, "STRATEGY")

    def _render_guide(self, guide) -> None:
        super()._render_guide(guide)
        if self._runtime_strategy_ready:
            self._render_runtime_strategy(guide.encounter_id)

    def _clear_guide(self) -> None:
        super()._clear_guide()
        if self._runtime_strategy_ready:
            self._clear_runtime_strategy()

    def _render_runtime_strategy(self, encounter_id: str) -> None:
        if self.runtime_guide_service is None:
            self._clear_runtime_strategy(
                "Reviewed runtime observation service is not configured for this Boss Guide."
            )
            return

        projection = self.runtime_guide_service.get(encounter_id)
        if not projection.has_runtime_evidence:
            self._clear_runtime_strategy(_RUNTIME_EVIDENCE_PLACEHOLDER)
            return

        self._populate_runtime_projection(projection)

    def _populate_runtime_projection(self, projection: EncounterGuideRuntimeProjection) -> None:
        operational_notes = sorted(
            projection.notes,
            key=lambda note: (
                _RUNTIME_NOTE_PRIORITY.get(note.key, 99),
                note.key.casefold(),
            ),
        )[:3]
        self.runtime_strategy_summary.setText(
            "\n".join(f"• {_operational_note(note)}" for note in operational_notes)
            if operational_notes
            else _RUNTIME_EVIDENCE_PLACEHOLDER
        )
        source_text = ", ".join(_compact_source_label(label) for label in projection.source_labels)
        source_text = source_text or "reviewed runtime corpus"
        self.runtime_evidence_source_label.setText(
            f"{projection.successful_kills} reviewed clear(s) • {source_text}"
        )

        self.runtime_notes_table.setRowCount(len(projection.notes))
        for row_index, note in enumerate(projection.notes):
            self.runtime_notes_table.setItem(row_index, 0, QTableWidgetItem(note.text))
            self.runtime_notes_table.setItem(
                row_index,
                1,
                QTableWidgetItem(note.confidence.replace("_", " ").title()),
            )
        self.runtime_notes_table.resizeRowsToContents()

        guidance_rows = sorted(
            projection.role_guidance,
            key=lambda row: (_priority_rank(row.priority), row.role.casefold(), row.guidance.casefold()),
        )
        self.runtime_guidance_table.setRowCount(len(guidance_rows))
        for row_index, row in enumerate(guidance_rows):
            values = (
                row.role.replace("_", " ").title(),
                row.priority.title(),
                row.guidance,
            )
            for column, value in enumerate(values):
                self.runtime_guidance_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(str(value)),
                )
        self.runtime_guidance_table.resizeRowsToContents()
        self._populate_runtime_glance_cards(projection, guidance_rows)

    def _populate_runtime_glance_cards(
        self,
        projection: EncounterGuideRuntimeProjection,
        guidance_rows,
    ) -> None:
        """Project a compact subset of reviewed runtime evidence onto overview cards."""
        overview = guidance_rows[:2]
        overview_text = (
            "\n".join(
                f"• {row.role.replace('_', ' ').title()}: {row.guidance}"
                for row in overview
            )
            if overview
            else _STRATEGY_PLACEHOLDER
        )
        self._set_glance_text(
            "runtime_strategy_overview_label",
            _STRATEGY_PLACEHOLDER,
            overview_text,
        )

        callouts = projection.notes[:3]
        callout_text = (
            "\n".join(f"• {note.text}" for note in callouts)
            if callouts
            else _CALLOUT_PLACEHOLDER
        )
        self._set_glance_text(
            "runtime_callouts_label",
            _CALLOUT_PLACEHOLDER,
            callout_text,
        )

        high_priority = [
            row for row in guidance_rows if str(row.priority or "").casefold() == "high"
        ][:3]
        reminders = high_priority or list(guidance_rows[:2])
        if reminders:
            reminder_text = "\n".join(
                f"• {row.role.replace('_', ' ').title()}: {row.guidance}"
                for row in reminders
            )
        else:
            reminder_text = _REMINDER_PLACEHOLDER
        self._set_glance_text(
            "runtime_reminders_label",
            _REMINDER_PLACEHOLDER,
            reminder_text,
        )

    def _clear_runtime_strategy(self, message: str | None = None) -> None:
        if not hasattr(self, "runtime_strategy_summary"):
            return
        self.runtime_strategy_summary.setText(message or _RUNTIME_EVIDENCE_PLACEHOLDER)
        self.runtime_evidence_source_label.setText("No reviewed runtime source.")
        self.runtime_notes_table.setRowCount(0)
        self.runtime_guidance_table.setRowCount(0)
        self._set_glance_text(
            "runtime_strategy_overview_label",
            _STRATEGY_PLACEHOLDER,
            _STRATEGY_PLACEHOLDER,
        )
        self._set_glance_text(
            "runtime_callouts_label",
            _CALLOUT_PLACEHOLDER,
            _CALLOUT_PLACEHOLDER,
        )
        self._set_glance_text(
            "runtime_reminders_label",
            _REMINDER_PLACEHOLDER,
            _REMINDER_PLACEHOLDER,
        )


def _layout_containing_widget(layout: QLayout, target: QWidget, seen: set[int] | None = None):
    seen = set() if seen is None else seen
    identity = id(layout)
    if identity in seen:
        return None
    seen.add(identity)

    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout

        nested = item.layout()
        if nested is not None:
            found = _layout_containing_widget(nested, target, seen)
            if found is not None:
                return found

        widget = item.widget()
        if widget is not None and widget.layout() is not None:
            found = _layout_containing_widget(widget.layout(), target, seen)
            if found is not None:
                return found
    return None


def _operational_note(note) -> str:
    canned = _RUNTIME_NOTE_GLANCE.get(note.key)
    if canned:
        return canned
    text = str(note.text or "").strip()
    if len(text) <= 110:
        return text
    return text[:107].rstrip() + "..."


def _compact_source_label(value: str) -> str:
    text = str(value or "").strip()
    if "eso logs" in text.casefold():
        return "ESO Logs corpus"
    return text


def _priority_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(str(value or "").casefold(), 99)


__all__ = ["RuntimeMechanicsPage"]
