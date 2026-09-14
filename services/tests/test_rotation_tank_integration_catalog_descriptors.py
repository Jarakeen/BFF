from services.service_catalog import SERVICE_CATALOG


def test_rotation_assignment_policy_and_tank_integration_services_are_catalogued() -> None:
    assignment_policy = SERVICE_CATALOG.get("rotation.assignment_policy.registry")
    provider_scope = SERVICE_CATALOG.get("rotation.tank.provider_scope")
    family_projection = SERVICE_CATALOG.get("rotation.tank.family_projection")

    assert assignment_policy is not None
    assert assignment_policy.implementation_path == (
        "services.rotation_assignment_policy_registry_service"
    )
    assert provider_scope is not None
    assert provider_scope.implementation_path == (
        "services.rotation_tank_provider_scope_service"
    )
    assert family_projection is not None
    assert family_projection.implementation_path == (
        "services.rotation_tank_family_projector_service"
    )
