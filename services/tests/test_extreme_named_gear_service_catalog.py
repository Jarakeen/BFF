from __future__ import annotations

from services.service_catalog import canonical_service_for


def test_extreme_named_gear_proof_services_are_discoverable() -> None:
    partial = canonical_service_for("partial_named_gear_physical_feasibility")
    ordinary = canonical_service_for("extreme_max_resource_ordinary_named_gear_search")
    special = canonical_service_for(
        "extreme_max_health_special_named_gear_branch_classification"
    )

    assert partial is not None
    assert ordinary is not None
    assert special is not None
    assert ordinary.dependencies == (
        "extreme.partial_named_gear_physical_feasibility",
    )
    assert special.dependencies == (
        "extreme.max_resource_ordinary_named_gear_search",
    )
    assert ordinary.implementation_path == (
        "services.extreme_max_resource_ordinary_named_gear_search_service"
    )
    assert special.implementation_path == (
        "services.extreme_max_health_special_named_gear_branch_service"
    )
