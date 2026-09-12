from __future__ import annotations

from services.service_catalog import canonical_service_for


def test_extreme_named_gear_proof_services_are_discoverable() -> None:
    partial = canonical_service_for("partial_named_gear_physical_feasibility")
    ordinary = canonical_service_for("extreme_max_resource_ordinary_named_gear_search")
    joint = canonical_service_for("extreme_max_resource_joint_named_gear_feasibility")
    shared_special = canonical_service_for(
        "extreme_max_resource_special_named_gear_branch_classification"
    )
    shared_execution = canonical_service_for(
        "extreme_max_resource_special_named_gear_execution"
    )
    shared_frontier = canonical_service_for(
        "extreme_max_resource_named_gear_candidate_frontier"
    )
    shared_adapter = canonical_service_for(
        "extreme_max_resource_named_gear_candidate_realization_adaptation"
    )
    special = canonical_service_for(
        "extreme_max_health_special_named_gear_branch_classification"
    )
    execution = canonical_service_for(
        "extreme_max_health_special_named_gear_execution"
    )
    frontier = canonical_service_for(
        "extreme_max_health_named_gear_candidate_frontier"
    )

    assert partial is not None
    assert ordinary is not None
    assert joint is not None
    assert shared_special is not None
    assert shared_execution is not None
    assert shared_frontier is not None
    assert shared_adapter is not None
    assert special is not None
    assert execution is not None
    assert frontier is not None

    assert ordinary.dependencies == (
        "extreme.partial_named_gear_physical_feasibility",
    )
    assert joint.dependencies == (
        "extreme.max_resource_ordinary_named_gear_search",
        "extreme.partial_named_gear_physical_feasibility",
    )
    assert shared_special.dependencies == (
        "extreme.max_resource_ordinary_named_gear_search",
    )
    assert shared_execution.dependencies == (
        "extreme.max_resource_special_named_gear_branches",
    )
    assert shared_frontier.dependencies == (
        "extreme.max_resource_joint_named_gear_feasibility",
        "extreme.max_resource_special_named_gear_branches",
        "extreme.partial_named_gear_physical_feasibility",
    )
    assert shared_adapter.dependencies == (
        "extreme.max_resource_named_gear_candidate_search",
    )
    assert special.dependencies == (
        "extreme.max_resource_ordinary_named_gear_search",
    )
    assert execution.dependencies == (
        "extreme.max_health_special_named_gear_branches",
    )
    assert frontier.dependencies == (
        "extreme.max_resource_ordinary_named_gear_search",
        "extreme.max_health_special_named_gear_branches",
        "extreme.partial_named_gear_physical_feasibility",
    )

    assert ordinary.implementation_path == (
        "services.extreme_max_resource_ordinary_named_gear_search_service"
    )
    assert joint.implementation_path == (
        "services.extreme_max_resource_joint_feasibility_search_service"
    )
    assert shared_special.implementation_path == (
        "services.extreme_max_resource_special_named_gear_branch_service"
    )
    assert shared_execution.implementation_path == (
        "services.extreme_max_resource_special_named_gear_execution_service"
    )
    assert shared_frontier.implementation_path == (
        "services.extreme_max_resource_named_gear_candidate_search_service"
    )
    assert shared_adapter.implementation_path == (
        "services.extreme_max_resource_named_gear_candidate_realization_adapter_service"
    )
    assert special.implementation_path == (
        "services.extreme_max_health_special_named_gear_branch_service"
    )
    assert execution.implementation_path == (
        "services.extreme_max_health_special_named_gear_execution_service"
    )
    assert frontier.implementation_path == (
        "services.extreme_max_health_named_gear_candidate_search_service"
    )
