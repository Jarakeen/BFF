from pathlib import Path

from services.extreme_record_execution_catalog_service import (
    ExtremeRecordExecutionCatalogService,
    ExtremeRecordExecutionStatus,
)
from ui import extreme_optimization_page, extreme_optimization_support


def test_extreme_lab_owns_critical_healing_through_canonical_catalog() -> None:
    page_source = Path(extreme_optimization_page.__file__).read_text(encoding="utf-8")
    support_source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")
    descriptor = ExtremeRecordExecutionCatalogService.descriptor("critical_healing")

    assert descriptor.status is ExtremeRecordExecutionStatus.READY
    assert descriptor.execution_family == "shared-static-stat"
    assert "self.service = ExtremeCompleteOptimizationService()" in page_source
    assert "self.execution_rows = ExtremeRecordExecutionCatalogService.descriptors()" in page_source

    # The installer may register the page and supply the complete blueprint layer,
    # but it must not append Critical Healing or replace the saved-build optimizer.
    assert "CRITICAL_HEALING_OBJECTIVE" not in support_source
    assert "page.service = ExtremeCompleteOptimizationService()" not in support_source
    assert "page.objective_combo.addItem(" not in support_source
