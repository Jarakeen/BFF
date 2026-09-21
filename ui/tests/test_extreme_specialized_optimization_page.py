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


def test_specialized_page_routes_supported_families_through_gateway() -> None:
    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")

    assert "class ExtremeSpecializedOptimizationPage(ExtremeOptimizationPage):" in source
    assert "database_path=self.service.database_path" in source
    assert "ExtremeSpecializedExecutionService.can_execute_without_extra_inputs" in source
    assert "ExtremeSpecializedExecutionService.can_execute_with_duration_input" in source
    assert "ExtremeSpecializedExecutionService.can_execute_with_combat_target_inputs" in source
    assert "ExtremeSpecializedExecutionService.requires_saved_build" in source
    assert "self._specialized_route_kind(objective_key)" in source
    assert "self.specialized_service.execute(" in source
    assert "duration_seconds=duration_seconds" in source
    assert "target_health=target_health" in source
    assert "target_resistance=target_resistance" in source
    assert "result.value_text" in source
    assert "super()._run_extreme_search()" in source


def test_all_zero_input_specialized_routes_are_explicit() -> None:
    for key in (
        "actual_heal",
        "critical_heal",
        "damage_shield",
        "bash_damage",
        "resource_sustain",
        "sustained_dps",
        "ultimate_generation",
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
        "invisibility_duration",
    ):
        assert ExtremeSpecializedExecutionService.can_execute_without_extra_inputs(key)

    assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("invisibility_uptime")
    assert not ExtremeSpecializedExecutionService.can_execute_without_extra_inputs("sustained_dps")


def test_invisibility_uptime_uses_generic_duration_route() -> None:
    assert ExtremeSpecializedExecutionService.can_execute_with_duration_input("invisibility_uptime")
    assert not ExtremeSpecializedExecutionService.requires_saved_build("invisibility_uptime")

    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")
    assert "if route_kind == \"duration\":" in source
    assert "QInputDialog.getDouble(" in source
    assert '"Comparison duration (seconds):"' in source


def test_saved_build_direct_routes_include_saved_rotation_records() -> None:
    for key in (
        "actual_heal",
        "critical_heal",
        "damage_shield",
        "bash_damage",
        "resource_sustain",
        "ultimate_generation",
    ):
        assert ExtremeSpecializedExecutionService.requires_saved_build(key)
    for key in (
        "movement_speed",
        "sprint_speed",
        "stealthed_movement_speed",
        "detection_radius_reduction",
        "invisibility_duration",
        "invisibility_uptime",
    ):
        assert not ExtremeSpecializedExecutionService.requires_saved_build(key)


def test_specialized_page_allows_scratch_execution_when_family_is_build_independent() -> None:
    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")

    assert "if route_kind is not None and (not scratch or not saved_build_required):" in source
    assert "build = None" in source
    assert "if not scratch:" in source
    assert "if scratch and saved_build_required:" in source



def test_sustained_dps_uses_generic_combat_target_route() -> None:
    assert ExtremeSpecializedExecutionService.can_execute_with_combat_target_inputs(
        "sustained_dps"
    )
    assert ExtremeSpecializedExecutionService.requires_saved_build("sustained_dps")

    source = Path(extreme_specialized_optimization_page.__file__).read_text(encoding="utf-8")
    assert 'return "combat_target"' in source
    assert 'if route_kind == "combat_target":' in source
    assert '"Target Health:"' in source
    assert '"Target resistance:"' in source
