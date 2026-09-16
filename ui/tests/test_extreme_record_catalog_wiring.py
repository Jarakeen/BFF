from __future__ import annotations

from pathlib import Path

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from ui import extreme_optimization_page, extreme_optimization_support


def test_extreme_page_uses_canonical_execution_catalog_for_objective_menu() -> None:
    source = Path(extreme_optimization_page.__file__).read_text(encoding="utf-8")

    assert "self.execution_rows = ExtremeRecordExecutionCatalogService.descriptors()" in source
    assert "for row in self.execution_rows:" in source
    assert "self.objective_combo.addItem(label, row.objective.key)" in source
    assert "for objective in EXTREME_OBJECTIVES:\n            self.objective_combo.addItem" not in source


def test_extreme_page_routes_ready_records_only_through_shared_static_runner() -> None:
    source = Path(extreme_optimization_page.__file__).read_text(encoding="utf-8")

    assert "self.service = ExtremeCompleteOptimizationService()" in source
    assert "descriptor.status is not ExtremeRecordExecutionStatus.READY" in source
    assert "No fallback calculation will be substituted." in source


def test_extreme_installer_does_not_append_or_reclassify_objectives() -> None:
    source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")

    assert "CRITICAL_HEALING_OBJECTIVE" not in source
    assert "objective_combo.addItem" not in source
    assert "page.service =" not in source
    assert "page.blueprint_service = ExtremeCompleteBlueprintService()" in source


def test_execution_catalog_still_covers_all_31_records_without_unclassified_family() -> None:
    rows = ExtremeRecordExecutionCatalogService.descriptors()

    assert len(rows) == 31
    assert all(row.execution_family != "unclassified" for row in rows)
    assert sum(row.status is ExtremeRecordExecutionStatus.READY for row in rows) == 19
    assert sum(row.status is ExtremeRecordExecutionStatus.SPECIALIZED for row in rows) == 4
    assert sum(row.status is ExtremeRecordExecutionStatus.PENDING for row in rows) == 8
