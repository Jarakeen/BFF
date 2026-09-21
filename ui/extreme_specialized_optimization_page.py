from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QPushButton, QTableWidgetItem

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionStatus,
)
from services.extreme_sustained_dps_search_service import (
    ExtremeSustainedDPSSearchResult,
    ExtremeSustainedDPSSearchService,
)
from services.extreme_specialized_execution_service import (
    ExtremeSpecializedExecutionResult,
    ExtremeSpecializedExecutionService,
)
from ui.extreme_optimization_page import ExtremeOptimizationPage


class ExtremeSpecializedOptimizationPage(ExtremeOptimizationPage):
    """Extreme Build Lab with one gateway for specialized execution families.

    The base page remains the owner of layout, saved builds, blueprint mode and
    shared-static execution. This subclass owns only specialized routing and the
    small set of family inputs that have canonical contracts.  Mechanics stay in
    family services instead of migrating into Qt code.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.specialized_service = ExtremeSpecializedExecutionService(
            database_path=self.service.database_path,
        )
        self.sustained_dps_search_service = ExtremeSustainedDPSSearchService(
            database_path=self.service.database_path,
        )
        self.saved_dps_search_button = QPushButton("Search Saved DD Builds")
        self.saved_dps_search_button.clicked.connect(self._run_saved_sustained_dps_search)
        self.header.add_context_widget(self.saved_dps_search_button)
        self._objective_changed()

    @staticmethod
    def _specialized_route_kind(objective_key: str) -> str | None:
        if ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(objective_key):
            return "direct"
        if ExtremeSpecializedExecutionService.can_execute_with_duration_input(objective_key):
            return "duration"
        if ExtremeSpecializedExecutionService.can_execute_with_combat_target_inputs(objective_key):
            return "combat_target"
        return None

    def _objective_changed(self, _index: int = -1) -> None:
        if not hasattr(self, "run_button") or not hasattr(self, "scope_text"):
            return

        descriptor = self._current_execution_descriptor()
        objective_key = descriptor.objective.key
        scratch = self.source_combo.currentData() == "scratch"
        if hasattr(self, "saved_dps_search_button"):
            saved_search_visible = objective_key == "sustained_dps" and not scratch
            self.saved_dps_search_button.setVisible(saved_search_visible)
            self.saved_dps_search_button.setEnabled(saved_search_visible)
        if hasattr(self, "change_table"):
            self.change_table.setHorizontalHeaderLabels(
                ["CHANGE", "BEFORE", "AFTER", "STAT GAIN"]
            )
        route_kind = (
            self._specialized_route_kind(objective_key)
            if descriptor.status is ExtremeRecordExecutionStatus.SPECIALIZED
            else None
        )
        saved_build_required = ExtremeSpecializedExecutionService.requires_saved_build(
            objective_key
        )
        if route_kind is not None and (not scratch or not saved_build_required):
            self.run_button.setEnabled(True)
            self.run_button.setToolTip("")
            if saved_build_required:
                context_line = "Saved-build starting context required."
            elif route_kind == "duration":
                context_line = (
                    "An explicit comparison duration is requested when the search runs; "
                    "provider windows are derived canonically."
                )
            elif route_kind == "combat_target":
                context_line = (
                    "Explicit target Health and resistance are requested when the search runs; "
                    "the saved RotationPlan owns the comparison horizon."
                )
            else:
                context_line = (
                    "No saved-build context required; canonical source package is searched directly."
                )
            self.scope_text.setPlainText(
                f"{descriptor.objective.label}\n"
                f"Shared execution family: {descriptor.execution_family}\n"
                f"{context_line}\n\n"
                "This record runs through the canonical specialized gateway. "
                "Unresolved proof boundaries remain visible in the result; no static fallback is substituted."
            )
            return

        super()._objective_changed(_index)

    def _run_extreme_search(self) -> None:
        objective_key = str(self.objective_combo.currentData() or "")
        descriptor = self._current_execution_descriptor()
        route_kind = (
            self._specialized_route_kind(objective_key)
            if descriptor.status is ExtremeRecordExecutionStatus.SPECIALIZED
            else None
        )
        if route_kind is None:
            super()._run_extreme_search()
            return

        scratch = self.source_combo.currentData() == "scratch"
        saved_build_required = ExtremeSpecializedExecutionService.requires_saved_build(
            objective_key
        )
        if scratch and saved_build_required:
            self.status.warning(
                f"{descriptor.objective.label} currently requires a saved-build starting context."
            )
            return

        build = None
        if not scratch:
            index = self.build_combo.currentData()
            if not isinstance(index, int) or not (0 <= index < len(self.builds)):
                self.status.warning("Choose a saved build first.")
                return
            build = self.builds[index]

        duration_seconds: float | None = None
        if route_kind == "duration":
            duration_seconds, accepted = QInputDialog.getDouble(
                self,
                f"{descriptor.objective.label} Duration",
                "Comparison duration (seconds):",
                60.0,
                1.0,
                86400.0,
                1,
            )
            if not accepted:
                return

        target_health: int | None = None
        target_resistance: float | None = None
        if route_kind == "combat_target":
            target_health, accepted = QInputDialog.getInt(
                self,
                f"{descriptor.objective.label} Target Health",
                "Target Health:",
                21200000,
                1,
                2147483647,
                1000,
            )
            if not accepted:
                return
            target_resistance, accepted = QInputDialog.getDouble(
                self,
                f"{descriptor.objective.label} Target Resistance",
                "Target resistance:",
                18200.0,
                0.0,
                1000000.0,
                0,
            )
            if not accepted:
                return

        active_bar = str(self.bar_combo.currentData() or "front")
        self.status.info(
            f"Searching {descriptor.objective.label} through the shared {descriptor.execution_family} engine."
        )
        try:
            result = self.specialized_service.execute(
                build,
                objective_key,
                active_bar=active_bar,
                duration_seconds=duration_seconds,
                target_health=target_health,
                target_resistance=target_resistance,
            )
        except Exception as exc:
            self.status.error(f"Extreme specialized search failed: {exc}")
            return

        self.current_result = result
        self._show_specialized_result(result)
        value = result.value_text or (
            "unresolved" if result.value is None else f"{result.value:,.0f}"
        )
        if result.global_maximum_proven:
            self.status.success(f"Extreme record proven: {result.label} {value}.")
        elif result.mechanic_complete:
            self.status.warning(
                f"Extreme search complete: {result.label} {value}; broader global-proof scope remains open."
            )
        else:
            self.status.warning(
                f"Extreme search produced a reviewed result for {result.label}: {value}; unresolved evidence remains."
            )

    def _run_saved_sustained_dps_search(self) -> None:
        objective_key = str(self.objective_combo.currentData() or "")
        if objective_key != "sustained_dps":
            self.status.warning("Saved DD library search is available only for MOST Sustained DPS.")
            return
        if self.source_combo.currentData() == "scratch":
            self.status.warning("Saved DD library search requires saved builds, not blueprint mode.")
            return

        target_health, accepted = QInputDialog.getInt(
            self,
            "MOST Sustained DPS Saved Search Target Health",
            "Target Health:",
            21200000,
            1,
            2147483647,
            1000,
        )
        if not accepted:
            return
        target_resistance, accepted = QInputDialog.getDouble(
            self,
            "MOST Sustained DPS Saved Search Target Resistance",
            "Target resistance:",
            18200.0,
            0.0,
            1000000.0,
            0,
        )
        if not accepted:
            return

        self.status.info(
            "Searching every eligible saved DD/DPS build with a canonical saved rotation."
        )
        try:
            result = self.sustained_dps_search_service.search(
                target_health=int(target_health),
                target_resistance=float(target_resistance),
            )
        except Exception as exc:
            self.status.error(f"Saved sustained-DPS search failed: {exc}")
            return

        self.current_result = result
        self._show_saved_sustained_dps_search_result(result)
        if result.search_complete_for_saved_denominator and result.leader is not None:
            self.status.success(
                "Saved DD library search complete; a unique saved-state leader is available."
            )
        else:
            self.status.warning(
                "Saved DD library search finished with unresolved or incomparable evidence."
            )

    def _show_saved_sustained_dps_search_result(
        self,
        result: ExtremeSustainedDPSSearchResult,
    ) -> None:
        leader = result.leader
        leader_value = None if leader is None else leader.modeled_dps
        self.baseline_value.setText("—")
        self.optimized_value.setText(
            "—" if leader_value is None else f"{leader_value:,.1f}"
        )
        self.delta_value.setText("—")

        self.change_table.setHorizontalHeaderLabels(
            ["CANDIDATE", "MODELED DPS", "HORIZON", "STATUS"]
        )
        self.change_table.setRowCount(0)
        ranked = ()
        if result.comparison is not None:
            ranked = result.comparison.ranked_candidates
        for candidate in ranked:
            row = self.change_table.rowCount()
            self.change_table.insertRow(row)
            self.change_table.setItem(row, 0, QTableWidgetItem(candidate.label))
            self.change_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    "—"
                    if candidate.modeled_dps is None
                    else f"{candidate.modeled_dps:,.1f}"
                ),
            )
            self.change_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    "—"
                    if candidate.duration_seconds is None
                    else f"{candidate.duration_seconds:g}s"
                ),
            )
            self.change_table.setItem(
                row,
                3,
                QTableWidgetItem(
                    "COMPLETE" if candidate.mechanic_complete else "UNRESOLVED"
                ),
            )
        self.change_table.resizeColumnsToContents()

        blocking = tuple(
            row
            for row in result.discovery.exclusions
            if bool(getattr(row, "blocking", True))
        )
        informational = tuple(
            row
            for row in result.discovery.exclusions
            if not bool(getattr(row, "blocking", True))
        )
        sections = [
            "SAVED LIBRARY SEARCH\n"
            f"  Eligible DD/DPS candidates: {result.discovery.candidate_count}\n"
            f"  Blocking exclusions: {len(blocking)}\n"
            f"  Informational non-DD exclusions: {len(informational)}\n"
            "  Scope: canonical saved user-state only, not a theoretical ESO-wide optimum."
        ]
        if blocking:
            sections.append(
                "BLOCKING EXCLUSIONS\n"
                + "\n".join(f"  ? {row.label}: {row.reason}" for row in blocking)
            )
        if informational:
            sections.append(
                "INFORMATIONAL EXCLUSIONS\n"
                + "\n".join(f"  ○ {row.label}: {row.reason}" for row in informational)
            )
        if result.unresolved:
            sections.append(
                "UNRESOLVED\n"
                + "\n".join(f"  ? {message}" for message in result.unresolved)
            )
        if result.evidence:
            sections.append(
                "EVIDENCE\n"
                + "\n".join(f"  ✓ {message}" for message in result.evidence)
            )
        self.scope_text.setPlainText("\n\n".join(sections))

    def _show_specialized_result(self, result: ExtremeSpecializedExecutionResult) -> None:
        self.change_table.setHorizontalHeaderLabels(
            ["CHANGE", "BEFORE", "AFTER", "STAT GAIN"]
        )
        value = result.value_text or (
            "—" if result.value is None else f"{result.value:,.0f}"
        )
        self.baseline_value.setText("—")
        self.optimized_value.setText(value)
        self.delta_value.setText("—")

        self.change_table.setRowCount(0)
        rows = [
            ("Execution family", result.execution_family),
            ("Mechanic complete", "YES" if result.mechanic_complete else "NO"),
            ("Global maximum proven", "YES" if result.global_maximum_proven else "NO"),
            *result.summary_rows,
        ]
        for label, display in rows:
            row = self.change_table.rowCount()
            self.change_table.insertRow(row)
            self.change_table.setItem(row, 0, QTableWidgetItem(str(label)))
            self.change_table.setItem(row, 1, QTableWidgetItem(str(display)))
            self.change_table.setItem(row, 2, QTableWidgetItem(""))
            self.change_table.setItem(row, 3, QTableWidgetItem(""))
        self.change_table.resizeColumnsToContents()

        searched = "\n".join(f"  ✓ {item}" for item in result.search_scope)
        omitted = "\n".join(f"  ○ {item}" for item in result.omitted_scope)
        unresolved = "\n".join(f"  ? {item}" for item in result.unresolved)
        sections = ["SEARCHED\n" + (searched or "  —")]
        sections.append("NOT YET SEARCHED\n" + (omitted or "  —"))
        if unresolved:
            sections.append("UNRESOLVED\n" + unresolved)
        self.scope_text.setPlainText("\n\n".join(sections))


__all__ = ["ExtremeSpecializedOptimizationPage"]
