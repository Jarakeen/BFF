from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from services.extreme_blueprint_service import ExtremeBlueprintResult, ExtremeBlueprintService
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
        self.blueprint_service = ExtremeBlueprintService()
        self.builds = ()
        self.current_result: ExtremeOptimizationResult | ExtremeBlueprintResult | None = None
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

        self.source_combo = QComboBox()
        self.source_combo.addItem("Tune Existing Toon", "existing")
        self.source_combo.addItem("Start From Scratch", "scratch")
        self.source_combo.setMinimumWidth(150)
        self.source_combo.currentIndexChanged.connect(self._source_changed)
        self.header.add_context_widget(self._context_field("MODE", self.source_combo))

        self.build_combo = QComboBox()
        self.build_combo.setMinimumWidth(180)
        self.header.add_context_widget(self._context_field("STARTING BUILD", self.build_combo))

        self.objective_combo = QComboBox()
        for objective in EXTREME_OBJECTIVES:
            self.objective_combo.addItem(objective.label, objective.key)
        self.objective_combo.setMinimumWidth(145)
        self.header.add_context_widget(self._context_field("MAXIMIZE", self.objective_combo))

        self.bar_combo = QComboBox()
        self.bar_combo.addItem("Front", "front")
        self.bar_combo.addItem("Back", "back")
        self.bar_combo.setMinimumWidth(80)
        self.header.add_context_widget(self._context_field("BAR", self.bar_combo))

        self.run_button = QPushButton("Commit Crimes Against Buildcraft")
        self.run_button.setProperty("primary", True)
        self.run_button.clicked.connect(self._run_extreme_search)
        self.header.add_context_widget(self.run_button)

        workspace = QWidget()
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(5)
        self.add_workspace(workspace)

        self.warning_card = FoundryCard("Experimental Boundary")
        warning_text = QLabel(
            "This tool deliberately ignores role viability, sustain, mechanics, and whether any sane raid lead would let you equip the result. "
            "Existing-toon mode keeps the original bounded mutation search. From-scratch mode also searches race and static 5-piece set packages, but does not invent class-passive or runtime proc math BFF cannot yet prove."
        )
        warning_text.setWordWrap(True)
        warning_text.setProperty("pageSubtitle", True)
        self.warning_card.addWidget(warning_text)
        self.warning_card.setMaximumHeight(86)
        root.addWidget(self.warning_card)

        self.summary_card = FoundryCard("Result")
        summary_row = QHBoxLayout()
        summary_row.setContentsMargins(0, 0, 0, 0)
        summary_row.setSpacing(4)
        self.baseline_value = QLabel("—")
        self.baseline_value.setProperty("metricValue", True)
        self.optimized_value = QLabel("—")
        self.optimized_value.setProperty("metricValue", True)
        self.delta_value = QLabel("—")
        self.delta_value.setProperty("metricValue", True)
        summary_row.addWidget(self._metric("BASELINE", self.baseline_value), 1)
        summary_row.addWidget(self._metric("EXTREME", self.optimized_value), 1)
        summary_row.addWidget(self._metric("GAIN", self.delta_value), 1)
        self.summary_card.addLayout(summary_row)
        self.summary_card.setMaximumHeight(92)
        root.addWidget(self.summary_card)

        self.changes_card = FoundryCard("Accepted Mutations")
        self.change_table = QTableWidget(0, 4)
        self.change_table.setHorizontalHeaderLabels(["CHANGE", "BEFORE", "AFTER", "STAT GAIN"])
        self.change_table.verticalHeader().setVisible(False)
        self.change_table.setAlternatingRowColors(True)
        self.change_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.change_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.change_table.horizontalHeader().setStretchLastSection(True)
        self.change_table.setMaximumHeight(230)
        self.changes_card.addWidget(self.change_table)
        root.addWidget(self.changes_card)

        self.blueprint_card = FoundryCard("From-Scratch Build Blueprint")
        self.blueprint_table = QTableWidget(0, 2)
        self.blueprint_table.setHorizontalHeaderLabels(["BUILD PART", "USE THIS"])
        self.blueprint_table.verticalHeader().setVisible(False)
        self.blueprint_table.setAlternatingRowColors(True)
        self.blueprint_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.blueprint_table.horizontalHeader().setStretchLastSection(True)
        self.blueprint_table.setMaximumHeight(300)
        self.blueprint_card.addWidget(self.blueprint_table)
        self.blueprint_card.setVisible(False)
        root.addWidget(self.blueprint_card)

        self.scope_card = FoundryCard("Search Boundary")
        self.scope_text = QTextEdit()
        self.scope_text.setReadOnly(True)
        self.scope_text.setMinimumHeight(72)
        self.scope_text.setMaximumHeight(105)
        self.scope_card.addWidget(self.scope_text)
        root.addWidget(self.scope_card)

        root.addStretch(1)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    @staticmethod
    def _context_field(label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        title = QLabel(label)
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)
        layout.addWidget(widget)
        return box

    @staticmethod
    def _metric(label: str, value: QLabel) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
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

        self._source_changed()
        if not self.builds and self.source_combo.currentData() == "existing":
            self.status.warning("No saved builds are available for extreme optimization.")

    def _source_changed(self, _index: int = -1) -> None:
        scratch = self.source_combo.currentData() == "scratch"
        self.build_combo.setEnabled(not scratch)
        self.changes_card.setVisible(not scratch)
        self.blueprint_card.setVisible(scratch)
        self.run_button.setText(
            "Invent a Terrible Character" if scratch else "Commit Crimes Against Buildcraft"
        )
        self.baseline_value.setText("—")
        self.optimized_value.setText("—")
        self.delta_value.setText("—")
        if scratch:
            self.scope_text.setPlainText(
                "FROM SCRATCH\n"
                "Starts with a neutral CP160 template, then searches race, static 5-piece set packages, attributes, Mundus, traits, enchants, and food.\n"
                "Class-specific passive/proc winners stay unresolved until BFF can prove them consistently across every class."
            )
        else:
            self.scope_text.clear()

    def _run_extreme_search(self) -> None:
        objective_key = str(self.objective_combo.currentData() or "")
        active_bar = str(self.bar_combo.currentData() or "front")

        if self.source_combo.currentData() == "scratch":
            self._run_blueprint_search(objective_key, active_bar)
            return

        index = self.build_combo.currentData()
        if not isinstance(index, int) or not (0 <= index < len(self.builds)):
            self.status.warning("Choose a saved build first.")
            return
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

    def _run_blueprint_search(self, objective_key: str, active_bar: str) -> None:
        self.status.info(
            "Starting from Jane / John Doe and searching the static build space. Dignity remains optional."
        )
        try:
            result = self.blueprint_service.optimize_from_scratch(
                objective_key,
                active_bar=active_bar,
            )
        except Exception as exc:
            self.status.error(f"From-scratch search failed: {exc}")
            return

        self.current_result = result
        self._show_blueprint_result(result)
        self.status.success(
            f"Blueprint complete: {result.objective.label} {format_extreme_value(result.objective, result.value)} inside the proven static search boundary."
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
            unresolved = "\n\nUnresolved candidates/effects were not used as invented values:\n" + "\n".join(
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

    def _show_blueprint_result(self, result: ExtremeBlueprintResult) -> None:
        self.baseline_value.setText("FROM SCRATCH")
        self.optimized_value.setText(format_extreme_value(result.objective, result.value))
        self.delta_value.setText("—")

        self.blueprint_table.setRowCount(0)
        for label, value in self._blueprint_rows(result):
            row = self.blueprint_table.rowCount()
            self.blueprint_table.insertRow(row)
            self.blueprint_table.setItem(row, 0, QTableWidgetItem(label))
            self.blueprint_table.setItem(row, 1, QTableWidgetItem(value))
        self.blueprint_table.resizeColumnsToContents()
        self.blueprint_table.horizontalHeader().setStretchLastSection(True)

        notes = "\n".join(f"• {note}" for note in result.notes)
        unresolved = ""
        if result.unresolved:
            unresolved = (
                f"\n\nUnresolved evidence retained: {len(result.unresolved)} item(s). "
                "Those values were not invented to improve the score."
            )
        self.scope_text.setPlainText(notes + unresolved)

    @staticmethod
    def _blueprint_rows(result: ExtremeBlueprintResult) -> tuple[tuple[str, str], ...]:
        build = result.build
        rows: list[tuple[str, str]] = [
            ("Race", result.race or "—"),
            ("Class", result.class_label),
            (
                "Class candidates",
                ", ".join(result.class_candidates),
            ),
            (
                "Attributes",
                f"Health {build.AttributeHealth} / Magicka {build.AttributeMagicka} / Stamina {build.AttributeStamina}",
            ),
            ("Mundus", str(build.Mundus or "—")),
        ]
        if result.set_package:
            rows.append(("5-piece sets", " + ".join(result.set_package)))

        for slot_name in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
            entry = build.Armor.get(slot_name, {})
            rows.append(
                (
                    slot_name,
                    ExtremeOptimizationPage._gear_text(
                        entry.get("Set", ""),
                        entry.get("Weight", ""),
                        entry.get("Enchant", ""),
                        entry.get("Trait", ""),
                    ),
                )
            )

        for label, slot in (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
            ("Front Weapon", build.FrontBarWeapon),
            ("Back Weapon", build.BackBarWeapon),
        ):
            rows.append(
                (
                    label,
                    ExtremeOptimizationPage._gear_text(
                        slot.Set,
                        slot.WeaponType,
                        slot.Enchant,
                        slot.Trait,
                    ),
                )
            )

        rows.extend(
            [
                ("Food", str(build.Food or "—")),
                ("Potion", str(build.Potion or "No static potion winner modeled")),
            ]
        )
        return tuple(rows)

    @staticmethod
    def _gear_text(name: str, detail: str, enchant: str, trait: str) -> str:
        parts = [str(value).strip() for value in (name, detail, enchant, trait) if str(value or "").strip()]
        return " • ".join(parts) if parts else "Open / no proven static winner"

    @staticmethod
    def _display_value(value: object) -> str:
        if isinstance(value, dict):
            return ", ".join(f"{key}={item}" for key, item in value.items())
        return str(value)
