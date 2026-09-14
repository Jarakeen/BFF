from services.service_catalog import default_service_catalog


def test_rotation_assignment_policy_and_tank_integration_services_are_catalogued() -> None:
    catalog = default_service_catalog()

    assert catalog.require("rotation.assignment_policy.registry").implementation_path == (
        "services.rotation_assignment_policy_registry_service"
    )
    assert catalog.require("rotation.tank.provider_scope").implementation_path == (
        "services.rotation_tank_provider_scope_service"
    )
    assert catalog.require("rotation.tank.family_projection").implementation_path == (
        "services.rotation_tank_family_projector_service"
    )
