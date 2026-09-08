from pathlib import Path

from ui import extreme_optimization_support


def test_extreme_lab_uses_complete_saved_build_service_and_exposes_critical_healing() -> None:
    source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")

    assert "ExtremeCompleteOptimizationService" in source
    assert "page.service = ExtremeCompleteOptimizationService()" in source
    assert "CRITICAL_HEALING_OBJECTIVE" in source
    assert "page.objective_combo.addItem(" in source
