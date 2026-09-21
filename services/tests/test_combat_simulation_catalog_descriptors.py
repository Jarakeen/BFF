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



def test_sequential_target_health_feedback_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get(
        "simulation.sequential_dd_health_feedback"
    )

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.combat_simulation_sequential_dd_damage_service"
    )
    assert (
        "combat_simulation_sequential_target_health_feedback"
        in descriptor.responsibilities
    )

    runner = SERVICE_CATALOG.get("simulation.saved_build_dd")
    assert runner is not None
    assert "simulation.sequential_dd_health_feedback" in runner.dependencies



def test_fight_termination_projection_is_catalogued() -> None:
    descriptor = SERVICE_CATALOG.get("simulation.fight_termination")

    assert descriptor is not None
    assert descriptor.implementation_path == (
        "services.combat_simulation_fight_termination_service"
    )
    assert "combat_simulation_fight_termination_projection" in descriptor.responsibilities

    runner = SERVICE_CATALOG.get("simulation.saved_build_dd")
    assert runner is not None
    assert "simulation.fight_termination" in runner.dependencies



def test_plan_attacker_state_and_damage_summary_are_catalogued() -> None:
    attacker = SERVICE_CATALOG.get("simulation.plan_attacker_state")
    summary = SERVICE_CATALOG.get("simulation.damage_summary")
    runner = SERVICE_CATALOG.get("simulation.saved_build_dd")

    assert attacker is not None
    assert attacker.implementation_path == (
        "services.combat_simulation_plan_attacker_state_service"
    )
    assert "combat_simulation_plan_owned_attacker_state" in attacker.responsibilities

    assert summary is not None
    assert summary.implementation_path == (
        "services.combat_simulation_damage_summary_service"
    )
    assert "combat_simulation_damage_summary" in summary.responsibilities

    assert runner is not None
    assert "simulation.plan_attacker_state" in runner.dependencies



def test_health_ordering_and_replay_services_are_catalogued() -> None:
    ordering = SERVICE_CATALOG.get("simulation.health_ordering")
    replay = SERVICE_CATALOG.get("simulation.deterministic_replay")

    assert ordering is not None
    assert ordering.implementation_path == (
        "services.combat_simulation_health_ordering_service"
    )
    assert "combat_simulation_health_ordering_guard" in ordering.responsibilities

    assert replay is not None
    assert replay.implementation_path == (
        "services.combat_simulation_deterministic_replay_service"
    )
    assert (
        "combat_simulation_deterministic_replay_verification"
        in replay.responsibilities
    )
