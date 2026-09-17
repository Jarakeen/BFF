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
    assert "ExtremeSpecializedExecutionService.requires_saved_build" in source
    assert "self.specialized_service.execute(" in source
    assert "result.value_text" in source
    assert "super()._run_extreme_search()" in source
    assert "No fallback" not in source


def test_current_zero_input_specialized_routes_are_explicit() -> None:
    for key in (
        "actual_heal",
        "critical_heal",
        "bash_damage",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
    ):
        assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)

    for key in (
        "damage_shield",
        "resource_sustain",
        "ultimate_generation",
        "invisibility_duration",
        "invisibility_uptime",
    ):
        assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)


def test_saved_build_direct_routes_are_explicit() -> None:
    for key in ("actual_heal", "critical_heal", "bash_damage"):
        assert ExtremeSpecializedExecutionService.requires_saved_build(key)
    for key in (
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
    ):
        assert not ExtremeSpecializedExecutionService.requires_saved_build(key)


def test_specialized_page_allows_scratch_execution_when_family_is_build_independent() -> None:
    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")

    assert "if direct_specialized and (not scratch or not saved_build_required):" in source
    assert "build = None" in source
    assert "if not scratch:" in source
    assert "if scratch and saved_build_required:" in source
