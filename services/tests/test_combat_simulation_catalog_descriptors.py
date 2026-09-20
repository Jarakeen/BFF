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
