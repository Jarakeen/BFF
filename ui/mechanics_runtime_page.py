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

    def _install_runtime_strategy_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        provenance = FoundryCard("Reviewed Runtime Evidence", "⌁").make_parchment().set_watermark(
            "feather", 0.08
        )
        self.runtime_strategy_summary = QLabel(
            "No reviewed runtime observations are available for this encounter."
        )
        self.runtime_strategy_summary.setWordWrap(True)
        self.runtime_strategy_summary.setProperty("muted", True)
        provenance.addWidget(self.runtime_strategy_summary)
        layout.addWidget(provenance)

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
            self._clear_runtime_strategy(
                "No reviewed runtime observations are available for this encounter."
            )
            return

        self._populate_runtime_projection(projection)

    def _populate_runtime_projection(self, projection: EncounterGuideRuntimeProjection) -> None:
        source_text = ", ".join(projection.source_labels) or "Reviewed runtime evidence"
        self.runtime_strategy_summary.setText(
            f"Reviewed real-run evidence: {projection.successful_kills} successful clear(s), "
            f"{projection.reviewed_windows} reviewed mechanic window(s). Source: {source_text}. "
            "These observations inform strategy only; they are not canonical encounter mechanics."
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
            rendered = [
                f"• {row.role.replace('_', ' ').title()}: {row.guidance}"
                for row in reminders
            ]
            rendered.append(
                f"• Reviewed runtime sample: {projection.successful_kills} successful clear(s)."
            )
            reminder_text = "\n".join(rendered)
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
        self.runtime_strategy_summary.setText(
            message or "No reviewed runtime observations are available for this encounter."
        )
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


def _priority_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(str(value or "").casefold(), 99)


__all__ = ["RuntimeMechanicsPage"]
