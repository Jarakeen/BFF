from services.service_catalog import SERVICE_CATALOG


def test_combat_simulation_outgoing_damage_bridge_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("simulation.outgoing_damage_bridge")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.combat_simulation_outgoing_damage_service"
    )
    assert (
        "combat_simulation_outgoing_damage_projection"
        in descriptor.responsibilities
    )
    assert "RotationActionDamageEvidenceProvider" in descriptor.inputs
    assert descriptor.encounter_aware is True



def test_saved_build_dd_simulation_services_are_catalogued() -> None:
    provider = SERVICE_CATALOG.get("simulation.saved_build_dd_provider")
    runner = SERVICE_CATALOG.get("simulation.saved_build_dd")

    assert provider is not None
    assert provider.implementation_path == (
        "services.combat_simulation_saved_build_dd_provider_service"
    )
    assert (
        "combat_simulation_saved_build_dd_provider_composition"
        in provider.responsibilities
    )

    assert runner is not None
    assert runner.implementation_path == (
        "services.combat_simulation_saved_build_dd_service"
    )
    assert "simulation.saved_build_dd_provider" in runner.dependencies
    assert "combat_simulation_saved_build_dd_execution" in runner.responsibilities
