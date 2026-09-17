from __future__ import annotations

from pathlib import Path

from services.extreme_specialized_execution_service import ExtremeSpecializedExecutionService
from ui import extreme_optimization_support, extreme_specialized_optimization_page


def test_installer_uses_specialized_page_subclass_without_reclassifying_objectives() -> None:
    support_source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")

    assert "from ui.extreme_specialized_optimization_page import ExtremeSpecializedOptimizationPage" in support_source
    assert "page = ExtremeSpecializedOptimizationPage()" in support_source
    assert "objective_combo.addItem" not in support_source
    assert "page.service =" not in support_source


def test_specialized_page_routes_only_zero_input_families_through_gateway() -> None:
    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")

    assert "class ExtremeSpecializedOptimizationPage(ExtremeOptimizationPage):" in source
    assert "database_path=self.service.database_path" in source
    assert "ExtremeSpecializedExecutionService.can_execute_without_extra_inputs" in source
    assert "self.specialized_service.execute(" in source
    assert "result.value_text" in source
    assert "super()._run_extreme_search()" in source
    assert "No fallback" not in source


def test_heal_and_movement_families_are_current_zero_input_specialized_routes() -> None:
    for key in (
        "actual_heal",
        "critical_heal",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
    ):
        assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)

    for key in (
        "damage_shield",
        "bash_damage",
        "resource_sustain",
        "ultimate_generation",
        "detection_radius_reduction",
        "invisibility_duration",
        "invisibility_uptime",
    ):
        assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)
