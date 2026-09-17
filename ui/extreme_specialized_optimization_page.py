from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionStatus,
)
from services.extreme_specialized_execution_service import (
    ExtremeSpecializedExecutionResult,
    ExtremeSpecializedExecutionService,
)
from ui.extreme_optimization_page import ExtremeOptimizationPage


class ExtremeSpecializedOptimizationPage(ExtremeOptimizationPage):
    """Extreme Build Lab with one gateway for specialized execution families.

    The base page remains the owner of layout, saved builds, blueprint mode and
    shared-static execution. This subclass only intercepts specialized records
    that the shared gateway can execute without additional scenario inputs.
    Future family forms can feed that same gateway instead of adding page-specific
    optimizers or monkeypatching the base class.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.specialized_service = ExtremeSpecializedExecutionService(
            database_path=self.service.database_path,
        )
        self._objective_changed()

    def _objective_changed(self, _index: int = -1) -> None:
        if not hasattr(self, "run_button") or not hasattr(self, "scope_text"):
            return

        descriptor = self._current_execution_descriptor()
        scratch = self.source_combo.currentData() == "scratch"
        direct_specialized = (
            descriptor.status is ExtremeRecordExecutionStatus.SPECIALIZED
            and ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(
                descriptor.objective.key
            )
        )
        if direct_specialized and not scratch:
            self.run_button.setEnabled(True)
            self.run_button.setToolTip("")
            self.scope_text.setPlainText(
                f"{descriptor.objective.label}\n"
                f"Shared execution family: {descriptor.execution_family}\n\n"
                "This record runs through the canonical specialized gateway. "
                "Unresolved proof boundaries remain visible in the result; no static fallback is substituted."
            )
            return

        super()._objective_changed(_index)

    def _run_extreme_search(self) -> None:
        objective_key = str(self.objective_combo.currentData() or "")
        descriptor = self._current_execution_descriptor()
        direct_specialized = (
            descriptor.status is ExtremeRecordExecutionStatus.SPECIALIZED
            and ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(
                objective_key
            )
        )
        if not direct_specialized:
            super()._run_extreme_search()
            return

        if self.source_combo.currentData() == "scratch":
            self.status.warning(
                f"{descriptor.objective.label} currently requires a saved-build starting context."
            )
            return

        index = self.build_combo.currentData()
        if not isinstance(index, int) or not (0 <= index < len(self.builds)):
            self.status.warning("Choose a saved build first.")
            return

        build = self.builds[index]
        active_bar = str(self.bar_combo.currentData() or "front")
        self.status.info(
            f"Searching {descriptor.objective.label} through the shared {descriptor.execution_family} engine."
        )
        try:
            result = self.specialized_service.execute(
                build,
                objective_key,
                active_bar=active_bar,
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

    def _show_specialized_result(self, result: ExtremeSpecializedExecutionResult) -> None:
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
