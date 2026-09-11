from __future__ import annotations

"""Fill missing Mechanics-page timelines and strategy from reviewed encounter evidence.

Canonical boss-guide phases remain authoritative. Reviewed evidence is used only as
presentation fallback when the persisted boss guide has no phase/timeline rows, and
for the Strategy tab which previously had no data source at all.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)
from ui.mechanics_timeline import phase_event


_INSTALLED = False


def _projection_service(self) -> EncounterGuideEvidenceProjectionService | None:
    service = getattr(self, "_guide_evidence_projection_service", None)
    if service is not None:
        return service
    guide_service = getattr(self, "guide_service", None)
    database = getattr(guide_service, "database", None)
    if database is None:
        return None
    data_root = Path(database).parent
    service = EncounterGuideEvidenceProjectionService(data_root)
    self._guide_evidence_projection_service = service
    return service


def _strategy_tab(self) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    self.strategy_evidence_summary = QLabel(
        "Reviewed encounter handling will appear here when evidence is available."
    )
    self.strategy_evidence_summary.setWordWrap(True)
    layout.addWidget(self.strategy_evidence_summary)

    self.strategy_evidence_table = QTableWidget(0, 3)
    self.strategy_evidence_table.setHorizontalHeaderLabels(
        ("Mechanic", "What It Does", "How To Handle It")
    )
    self.strategy_evidence_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.strategy_evidence_table.setWordWrap(True)
    self.strategy_evidence_table.verticalHeader().setVisible(False)
    header = self.strategy_evidence_table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    layout.addWidget(self.strategy_evidence_table, 1)

    self.strategy_evidence_callouts = QLabel()
    self.strategy_evidence_callouts.setWordWrap(True)
    self.strategy_evidence_callouts.setProperty("parchment", True)
    layout.addWidget(self.strategy_evidence_callouts)
    return tab


def _install_strategy_tab(self) -> None:
    tabs = getattr(self, "tabs", None)
    if tabs is None:
        return
    for index in range(tabs.count()):
        if tabs.tabText(index).strip().upper() != "STRATEGY":
            continue
        tabs.removeTab(index)
        tabs.insertTab(index, _strategy_tab(self), "STRATEGY")
        return


def _render_strategy(self, projection) -> None:
    table = getattr(self, "strategy_evidence_table", None)
    if table is None:
        return

    rows = projection.strategy
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        mechanic = row.mechanic
        if row.common_names:
            mechanic = f"{mechanic}\nCommon: {', '.join(row.common_names)}"
        values = (mechanic, row.summary, row.mitigation)
        for column, value in enumerate(values):
            table.setItem(row_index, column, QTableWidgetItem(str(value)))
    table.resizeRowsToContents()

    if rows:
        self.strategy_evidence_summary.setText(
            f"{len(rows)} reviewed mechanic strategy row(s) projected from encounter evidence. "
            "Canonical encounter structure remains authoritative."
        )
    else:
        self.strategy_evidence_summary.setText(
            "No reviewed strategy evidence is available for this encounter yet."
        )

    callouts = projection.callouts
    self.strategy_evidence_callouts.setText(
        "IMPORTANT CALL OUTS\n" + "\n".join(f"• {value}" for value in callouts)
        if callouts
        else "No reviewed raid callouts are available yet."
    )


def install() -> None:
    """Install reviewed evidence fallback onto the finished Mechanics page."""

    global _INSTALLED
    if _INSTALLED:
        return

    from ui.mechanics_page import MechanicsPage

    original_init = MechanicsPage.__init__
    original_render = MechanicsPage._render_guide
    original_clear = MechanicsPage._clear_guide

    def render_with_evidence(self, guide) -> None:
        original_render(self, guide)
        service = _projection_service(self)
        if service is None:
            return
        projection = service.get(guide.encounter_id, guide.name)

        # Canonical / persisted phase data always wins. Only fill the timeline
        # when the boss guide has no explicit phase rows.
        if not guide.phases and projection.timeline:
            self.phase_table.setRowCount(len(projection.timeline))
            for row_index, row in enumerate(projection.timeline):
                for column, value in enumerate((row.marker, row.label, row.detail)):
                    self.phase_table.setItem(row_index, column, QTableWidgetItem(str(value)))
            self.phase_table.resizeRowsToContents()
            self.timeline.set_events(
                [
                    phase_event(
                        marker=row.marker or "?",
                        label=row.label or "Phase",
                        detail=row.detail or "Reviewed encounter evidence.",
                    )
                    for row in projection.timeline
                ]
            )

        _render_strategy(self, projection)

        if getattr(self, "coverage_notes", None):
            timeline_source = "canonical" if guide.phases else "reviewed evidence fallback"
            timeline_count = len(guide.phases) if guide.phases else len(projection.timeline)
            self.coverage_notes[-1].setText(
                f"• Timeline: {timeline_count} row(s), {timeline_source}; "
                f"strategy: {len(projection.strategy)} reviewed row(s)."
            )

        if hasattr(self, "status"):
            fallback_note = (
                f", {len(projection.timeline)} reviewed timeline fallback row(s)"
                if not guide.phases and projection.timeline
                else ""
            )
            self.status.success(
                f"Loaded {guide.name}: {len(guide.abilities)} named ability record(s), "
                f"{len(guide.phases)} canonical phase record(s){fallback_note}, "
                f"{len(projection.strategy)} strategy row(s)."
            )

    def clear_with_evidence(self) -> None:
        original_clear(self)
        table = getattr(self, "strategy_evidence_table", None)
        if table is not None:
            table.setRowCount(0)
        summary = getattr(self, "strategy_evidence_summary", None)
        if summary is not None:
            summary.setText("Select an encounter to view reviewed strategy evidence.")
        callouts = getattr(self, "strategy_evidence_callouts", None)
        if callouts is not None:
            callouts.setText("No encounter selected.")

    def init_with_evidence_guide(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        _projection_service(self)
        _install_strategy_tab(self)
        guide_service = getattr(self, "guide_service", None)
        encounter_id = self.boss_combo.currentData() if hasattr(self, "boss_combo") else None
        if guide_service is not None and encounter_id:
            render_with_evidence(self, guide_service.get(str(encounter_id)))

    MechanicsPage._render_guide = render_with_evidence
    MechanicsPage._clear_guide = clear_with_evidence
    MechanicsPage.__init__ = init_with_evidence_guide
    _INSTALLED = True
