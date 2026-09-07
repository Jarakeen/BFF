from __future__ import annotations

from PySide6.QtCore import Qt
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

from services.extreme_optimization_service import (
    EXTREME_OBJECTIVES,
    ExtremeOptimizationResult,
    ExtremeOptimizationService,
    format_extreme_value,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


class ExtremeOptimizationPage(FoundryPage):
    """Tools workspace for deliberately absurd single-stat builds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = ExtremeOptimizationService()
        self.builds = ()
        self.current_result: ExtremeOptimizationResult | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Extreme Build Lab",
            subtitle=(
                "Max one stat without pretending the result is a sensible raid build. "
                "Canonical character-sheet math only."
            ),
            department="TOOLS • QUESTIONABLE DECISIONS",
        )
        self.set_header(self.header)

        self.build_combo = QComboBox()
        self.build_combo.setMinimumWidth(250)
        self.header.add_context_widget(self._context_field("STARTING BUILD", self.build_combo))

        self.objective_combo = QComboBox()
        for objective in EXTREME_OBJECTIVES:
            self.objective_combo.addItem(objective.label, objective.key)
        self.objective_combo.setMinimumWidth(190)
        self.header.add_context_widget(self._context_field("MAXIMIZE", self.objective_combo))

        self.bar_combo = QComboBox()
        self.bar_combo.addItem("Front Bar", "front")
        self.bar_combo.addItem("Back Bar", "back")
        self.header.add_context_widget(self._context_field("ACTIVE BAR", self.bar_combo))

        run_button = QPushButton("Commit Crimes Against Buildcraft")
        run_button.setProperty("primary", True)
        run_button.clicked.connect(self._run_extreme_search)
        self.header.add_context_widget(run_button)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        self.add_workspace(workspace)

        warning = FoundryCard("Experimental Boundary")
        warning_text = QLabel(
            "This tool deliberately ignores role viability, sustain, mechanics, and whether any sane raid lead would let you equip the result. "
            "It searches only BFF's currently modeled static mutation families. Gear-set replacement and runtime/group proc stacking are not yet part of the proof, so the result is the best BFF can prove inside the listed search boundary, not a claim about the absolute global ESO maximum."
        )
        warning_text.setWordWrap(True)
        warning_text.setProperty("pageSubtitle", True)
        warning.addWidget(warning_text)
        root.addWidget(warning)

        summary = FoundryCard("Result")
        summary_row = QHBoxLayout()
        self.baseline_value = QLabel("—")
        self.baseline_value.setProperty("metricValue", True)
        self.optimized_value = QLabel("—")
        self.optimized_value.setProperty("metricValue", True)
        self.delta_value = QLabel("—")
        self.delta_value.setProperty("metricValue", True)
        summary_row.addWidget(self._metric("BASELINE", self.baseline_value), 1)
        summary_row.addWidget(self._metric("EXTREME", self.optimized_value), 1)
        summary_row.addWidget(self._metric("GAIN", self.delta_value), 1)
        summary.addLayout(summary_row)
        root.addWidget(summary)

        changes = FoundryCard("Accepted Mutations")
        self.change_table = QTableWidget(0, 4)
        self.change_table.setHorizontalHeaderLabels(["CHANGE", "BEFORE", "AFTER", "STAT GAIN"])
        self.change_table.verticalHeader().setVisible(False)
        self.change_table.setAlternatingRowColors(True)
        self.change_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.change_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.change_table.horizontalHeader().setStretchLastSection(True)
        changes.addWidget(self.change_table)
        root.addWidget(changes, 1)

        scope = FoundryCard("Search Boundary")
        self.scope_text = QTextEdit()
        self.scope_text.setReadOnly(True)
        self.scope_text.setMinimumHeight(150)
        scope.addWidget(self.scope_text)
        root.addWidget(scope)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _context_field(label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        title = QLabel(label)
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)
        layout.addWidget(widget)
        return box

    @staticmethod
    def _metric(label: str, value: QLabel) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        heading = QLabel(label)
        heading.setProperty("sidebarHeading", True)
        layout.addWidget(heading)
        layout.addWidget(value)
        return box

    def refresh(self) -> None:
        selected = self.build_combo.currentData() if hasattr(self, "build_combo") else None
        try:
            self.builds = self.service.saved_builds()
        except Exception as exc:
            self.builds = ()
            self.status.error(f"Could not load saved builds: {exc}")
            return

        self.build_combo.blockSignals(True)
        try:
            self.build_combo.clear()
            for index, build in enumerate(self.builds):
                player = str(build.Name or build.Gamertag or "Unnamed").strip()
                build_name = str(build.BuildName or "Current Build").strip()
                self.build_combo.addItem(f"{player} • {build_name}", index)
            if isinstance(selected, int) and 0 <= selected < len(self.builds):
                self.build_combo.setCurrentIndex(selected)
        finally:
            self.build_combo.blockSignals(False)

        if not self.builds:
            self.status.warning("No saved builds are available for extreme optimization.")

    def _run_extreme_search(self) -> None:
        index = self.build_combo.currentData()
        if not isinstance(index, int) or not (0 <= index < len(self.builds)):
            self.status.warning("Choose a saved build first.")
            return
        objective_key = str(self.objective_combo.currentData() or "")
        active_bar = str(self.bar_combo.currentData() or "front")
        build = self.builds[index]
        self.status.info("Searching the modeled build space. Common sense has been temporarily disabled.")
        try:
            result = self.service.optimize(build, objective_key, active_bar=active_bar)
        except Exception as exc:
            self.status.error(f"Extreme search failed: {exc}")
            return

        self.current_result = result
        self._show_result(result)
        self.status.success(
            f"Extreme search complete: {result.objective.label} {format_extreme_value(result.objective, result.optimized_value)}."
        )

    def _show_result(self, result: ExtremeOptimizationResult) -> None:
        self.baseline_value.setText(format_extreme_value(result.objective, result.baseline_value))
        self.optimized_value.setText(format_extreme_value(result.objective, result.optimized_value))
        self.delta_value.setText(format_extreme_value(result.objective, result.delta))

        self.change_table.setRowCount(0)
        for step in result.steps:
            row = self.change_table.rowCount()
            self.change_table.insertRow(row)
            values = (
                step.path,
                self._display_value(step.before),
                self._display_value(step.after),
                format_extreme_value(result.objective, step.delta),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.change_table.setItem(row, column, item)
        self.change_table.resizeColumnsToContents()

        searched = "\n".join(f"  ✓ {item}" for item in result.search_scope)
        omitted = "\n".join(f"  ○ {item}" for item in result.omitted_scope)
        unresolved = ""
        if result.unresolved:
            unresolved = "\n\nUnresolved candidates/effects were not used for ranking:\n" + "\n".join(
                f"  ? {message}" for message in result.unresolved[:20]
            )
            if len(result.unresolved) > 20:
                unresolved += f"\n  ? … {len(result.unresolved) - 20} more"
        self.scope_text.setPlainText(
            "SEARCHED\n"
            + searched
            + "\n\nNOT YET SEARCHED\n"
            + omitted
            + unresolved
        )

    @staticmethod
    def _display_value(value: object) -> str:
        if isinstance(value, dict):
            return ", ".join(f"{key}={item}" for key, item in value.items())
        return str(value)
