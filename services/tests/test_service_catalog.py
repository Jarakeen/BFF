from __future__ import annotations

import pytest

from services.service_catalog import (
    CapabilityStatus,
    EvidenceClass,
    SERVICE_CATALOG,
    ServiceAuthority,
    ServiceBehavior,
    ServiceCatalog,
    ServiceCatalogAmbiguityError,
    ServiceDescriptor,
    ServiceLifecycle,
    canonical_service_for,
    capability_status,
    services_by_domain,
    services_consuming,
    services_producing,
)


def _descriptor(
    service_id: str,
    *,
    responsibility: str = "thing",
    lifecycle: ServiceLifecycle = ServiceLifecycle.IMPLEMENTED,
    authority: ServiceAuthority = ServiceAuthority.CANONICAL,
) -> ServiceDescriptor:
    return ServiceDescriptor(
        service_id=service_id,
        domain="test",
        purpose="test service",
        implementation_path="services.test_service",
        lifecycle=lifecycle,
        authority=authority,
        responsibilities=(responsibility,),
    )


def test_catalog_discovers_canonical_service_without_executing_it() -> None:
    descriptor = canonical_service_for("rotation_candidate_generation")

    assert descriptor is not None
    assert descriptor.service_id == "rotation.candidate_generation"
    assert descriptor.implementation_path == "services.rotation_candidate_generation_service"


def test_domain_and_type_queries_are_read_only_metadata() -> None:
    rotation = services_by_domain("rotation", available_only=True)

    assert {row.service_id for row in rotation} >= {
        "rotation.duration_refinement",
        "rotation.candidate_generation",
    }
    assert "rotation.candidate_generation" in {
        row.service_id for row in services_consuming("RotationPlan")
    }
    assert "rotation.candidate_generation" in {
        row.service_id for row in services_producing("GeneratedRotationCandidate")
    }


def test_capability_status_distinguishes_implemented_planned_and_missing() -> None:
    catalog = ServiceCatalog(
        (
            _descriptor("implemented"),
            _descriptor(
                "planned",
                responsibility="future",
                lifecycle=ServiceLifecycle.PLANNED,
            ),
        )
    )

    assert catalog.capability_status("thing") is CapabilityStatus.IMPLEMENTED
    assert catalog.capability_status("future") is CapabilityStatus.PLANNED
    assert catalog.capability_status("missing") is CapabilityStatus.UNAVAILABLE


def test_duplicate_canonical_responsibility_is_not_silently_selected() -> None:
    catalog = ServiceCatalog((_descriptor("one"), _descriptor("two")))

    with pytest.raises(ServiceCatalogAmbiguityError):
        catalog.canonical_for("thing")


def test_catalog_keeps_observational_and_game_mechanic_evidence_distinct() -> None:
    encounter = SERVICE_CATALOG.get("encounter.repository")
    extreme = SERVICE_CATALOG.get("extreme.actual_heal_optimization")

    assert encounter is not None
    assert extreme is not None
    assert encounter.evidence_class is EvidenceClass.GAME_MECHANIC
    assert extreme.evidence_class is EvidenceClass.GAME_MECHANIC
    assert capability_status("canonical_encounter_access") is CapabilityStatus.IMPLEMENTED


def test_dependencies_are_descriptor_relationships_not_runtime_resolution() -> None:
    dependencies = SERVICE_CATALOG.dependencies_of("team.prescription.pipeline")

    assert {row.service_id for row in dependencies} == {
        "team.prescription.candidate_pool",
        "team.prescription.optimizer",
        "team.prescription.candidate_source",
    }


def test_logs_and_calibration_services_preserve_evidence_boundaries() -> None:
    composition = SERVICE_CATALOG.get("logs.esologs.composition_evidence")
    discovery = SERVICE_CATALOG.get("logs.esologs.healer_sqlite_discovery")
    aliases = SERVICE_CATALOG.get("logs.esologs.canonical_skill_alias")
    btv = SERVICE_CATALOG.get("calibration.btv.benchmark_evidence")
    dashboard = SERVICE_CATALOG.get("performance.dashboard")

    assert composition is not None
    assert discovery is not None
    assert aliases is not None
    assert btv is not None
    assert dashboard is not None

    assert composition.evidence_class is EvidenceClass.OBSERVATIONAL
    assert discovery.evidence_class is EvidenceClass.OBSERVATIONAL
    assert aliases.evidence_class is EvidenceClass.MIXED
    assert btv.evidence_class is EvidenceClass.CALIBRATION
    assert btv.behavior is ServiceBehavior.CALIBRATED
    assert dashboard.evidence_class is EvidenceClass.OBSERVATIONAL
    assert "numeric ESO ability IDs are aliases only" in aliases.notes


def test_team_provider_decision_spine_is_discoverable() -> None:
    decision = canonical_service_for("team_provider_workload_decision")

    assert decision is not None
    assert decision.service_id == "team.provider.workload_decision"
    assert {row.service_id for row in SERVICE_CATALOG.dependencies_of(decision.service_id)} == {
        "team.provider.workload_candidate",
        "team.provider.workload_frontier",
    }
    assert capability_status("team_provider_recipient_coverage") is CapabilityStatus.IMPLEMENTED
    assert capability_status("team_provider_temporal_coverage") is CapabilityStatus.IMPLEMENTED


def test_performance_snapshot_is_ui_safe_observational_capability() -> None:
    dashboard = canonical_service_for("performance_dashboard_snapshot")

    assert dashboard is not None
    assert dashboard.ui_safe is True
    assert dashboard.encounter_aware is True
    assert dashboard.evidence_class is EvidenceClass.OBSERVATIONAL
    assert set(dashboard.roles) == {"Tank", "Healer", "DPS"}


def test_comp_maker_whole_team_optimizer_owns_candidate_selection() -> None:
    optimizer = canonical_service_for("comp_builder_whole_team_candidate_optimization")
    prescription = canonical_service_for(
        "comp_builder_authoritative_prescription_materialization"
    )

    assert optimizer is not None
    assert prescription is not None
    assert optimizer.service_id == "comp.builder.team_candidate_optimizer"
    assert prescription.service_id == "comp.builder.authoritative_prescription"
    assert optimizer.service_id in prescription.dependencies
    assert "must not rerank" in prescription.notes


def test_comp_provider_evidence_stays_separate_from_strategy_policy() -> None:
    provider = SERVICE_CATALOG.get("comp.builder.provider_evidence")
    strategy = SERVICE_CATALOG.get("comp.builder.strategy_evidence")

    assert provider is not None
    assert strategy is not None
    assert provider.evidence_class is EvidenceClass.GAME_MECHANIC
    assert strategy.evidence_class is EvidenceClass.POLICY
    assert strategy.behavior is ServiceBehavior.HEURISTIC
    assert provider.service_id in strategy.dependencies


def test_team_optimization_static_boundary_is_explicit() -> None:
    analysis = canonical_service_for("team_optimization_canonical_static_analysis")
    comparison = canonical_service_for("team_optimization_static_comparison")

    assert analysis is not None
    assert comparison is not None
    assert analysis.service_id == "team.optimization.canonical_static_analysis"
    assert analysis.service_id in comparison.dependencies
    assert "cannot prove encounter uptime" in analysis.notes
    assert "without choosing an encounter-aware raid winner" in comparison.purpose


def test_comp_novelty_is_observational_and_never_hard_validity() -> None:
    novelty = canonical_service_for("comp_builder_novelty_evidence")

    assert novelty is not None
    assert novelty.service_id == "comp.builder.novelty_evidence"
    assert novelty.evidence_class is EvidenceClass.OBSERVATIONAL
    assert novelty.behavior is ServiceBehavior.CALIBRATED
    assert "descriptive evidence only" in novelty.notes
    assert "hard validity" in novelty.notes


def test_prescription_generation_and_constraints_preserve_unresolved_evidence() -> None:
    generator = canonical_service_for("team_prescription_saved_build_generation")
    coverage = canonical_service_for("team_prescription_provider_coverage_projection")
    constraints = canonical_service_for("team_prescription_slot_build_constraints")

    assert generator is not None
    assert coverage is not None
    assert constraints is not None
    assert generator.service_id == "team.prescription.saved_build_generator"
    assert coverage.service_id == "team.prescription.provider_coverage_projection"
    assert constraints.service_id == "team.prescription.slot_constraints"
    assert "open chairs remain unresolved" in generator.notes
    assert "Phase 11 provider assignments remain authoritative" in coverage.notes
    assert "hard gates" in constraints.notes



def test_combat_simulation_services_are_canonical_and_discoverable() -> None:
    kernel = canonical_service_for("combat_simulation_deterministic_execution")
    saved_dd = canonical_service_for("combat_simulation_saved_build_dd_execution")
    summary = canonical_service_for("combat_simulation_damage_summary")
    replay = canonical_service_for("combat_simulation_deterministic_replay_verification")
    snapshot = canonical_service_for("combat_simulation_snapshot_projection")

    assert kernel is not None
    assert saved_dd is not None
    assert summary is not None
    assert replay is not None
    assert snapshot is not None

    assert kernel.service_id == "combat.simulation.kernel"
    assert saved_dd.service_id == "simulation.saved_build_dd"
    assert summary.service_id == "simulation.damage_summary"
    assert replay.service_id == "simulation.deterministic_replay"
    assert snapshot.service_id == "combat.simulation.snapshot"

    assert capability_status(
        "combat_simulation_deterministic_execution"
    ) is CapabilityStatus.IMPLEMENTED
    assert {row.service_id for row in services_by_domain("combat", available_only=True)} >= {
        "combat.simulation.kernel",
        "combat.simulation.snapshot",
    }
    assert {row.service_id for row in services_by_domain("simulation", available_only=True)} >= {
        "simulation.saved_build_dd",
        "simulation.damage_summary",
        "simulation.deterministic_replay",
    }


def test_combat_simulation_catalog_preserves_authority_boundaries() -> None:
    kernel = SERVICE_CATALOG.get("combat.simulation.kernel")
    saved_dd = SERVICE_CATALOG.get("simulation.saved_build_dd")
    summary = SERVICE_CATALOG.get("simulation.damage_summary")

    assert kernel is not None
    assert saved_dd is not None
    assert summary is not None

    assert kernel.behavior is ServiceBehavior.DETERMINISTIC
    assert kernel.evidence_class is EvidenceClass.MIXED
    assert kernel.encounter_aware is True
    assert "does not invent" in kernel.notes

    assert "simulation.saved_build_dd_provider" in saved_dd.dependencies
    assert "never coerced to zero" in saved_dd.notes

    assert summary.service_id == "simulation.damage_summary"
    assert summary.behavior is ServiceBehavior.DETERMINISTIC
    assert "withheld" in summary.notes



def test_extreme_sustained_dps_consumes_combat_simulation_authority() -> None:
    sustained = canonical_service_for("extreme_saved_rotation_sustained_dps_record")

    assert sustained is not None
    assert sustained.service_id == "extreme.sustained_dps.saved_rotation"
    assert sustained.behavior is ServiceBehavior.DETERMINISTIC
    assert sustained.encounter_aware is True
    assert set(sustained.roles) == {"DPS"}
    assert {
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(sustained.service_id)
    } == {
        "simulation.saved_build_dd",
        "simulation.damage_summary",
    }
    assert "lower bound" in sustained.notes
    assert "optimization responsibility" in sustained.notes



def test_combat_simulation_core_responsibilities_have_one_canonical_authority() -> None:
    for responsibility in (
        "combat_simulation_saved_build_dd_execution",
        "combat_simulation_damage_summary",
        "combat_simulation_deterministic_replay_verification",
    ):
        matches = tuple(
            row
            for row in SERVICE_CATALOG.descriptors
            if responsibility in row.responsibilities
            and row.authority is ServiceAuthority.CANONICAL
            and row.lifecycle is not ServiceLifecycle.DISABLED
        )
        assert len(matches) == 1, (
            responsibility,
            tuple(row.service_id for row in matches),
        )



def test_sustained_dps_comparison_consumes_single_witness_evaluator() -> None:
    comparison = canonical_service_for("extreme_sustained_dps_candidate_comparison")

    assert comparison is not None
    assert comparison.service_id == "extreme.sustained_dps.comparison"
    assert comparison.behavior is ServiceBehavior.DETERMINISTIC
    assert comparison.encounter_aware is True
    assert set(comparison.roles) == {"DPS"}
    assert {
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(comparison.service_id)
    } == {"extreme.sustained_dps.saved_rotation"}
    assert "explicitly supplied comparable candidate set" in comparison.notes
    assert "does not prove the global Extreme maximum" in comparison.notes


def test_sustained_dps_discovery_is_canonical_saved_state_authority() -> None:
    discovery = canonical_service_for("extreme_sustained_dps_candidate_discovery")

    assert discovery is not None
    assert discovery.service_id == "extreme.sustained_dps.discovery"
    assert discovery.behavior is ServiceBehavior.DETERMINISTIC
    assert discovery.encounter_aware is False
    assert set(discovery.roles) == {"DPS"}
    assert SERVICE_CATALOG.dependencies_of(discovery.service_id) == ()


def test_sustained_dps_saved_state_search_consumes_discovery_and_comparison() -> None:
    search = canonical_service_for("extreme_sustained_dps_saved_state_search")

    assert search is not None
    assert search.service_id == "extreme.sustained_dps.saved_state_search"
    assert search.behavior is ServiceBehavior.DETERMINISTIC
    assert search.encounter_aware is True
    assert set(search.roles) == {"DPS"}
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(search.service_id)
    ) == (
        "extreme.sustained_dps.discovery",
        "extreme.sustained_dps.comparison",
    )
    assert "saved user-state denominator" in search.notes
    assert "does not generate unsaved builds/rotations" in search.notes


def test_sustained_dps_generated_frontier_is_structural_generation_authority() -> None:
    frontier = canonical_service_for("extreme_sustained_dps_generated_structural_frontier")

    assert frontier is not None
    assert frontier.service_id == "extreme.sustained_dps.generated_frontier"
    assert frontier.behavior is ServiceBehavior.DETERMINISTIC
    assert frontier.encounter_aware is False
    assert set(frontier.roles) == {"DPS"}
    assert SERVICE_CATALOG.dependencies_of(frontier.service_id) == ()
    assert "64-point attributes" in frontier.notes
    assert "remain explicit deferred axes" in frontier.notes


def test_sustained_dps_pruning_consumes_generated_frontier() -> None:
    pruning = canonical_service_for("extreme_sustained_dps_proof_safe_pruning")

    assert pruning is not None
    assert pruning.service_id == "extreme.sustained_dps.pruning"
    assert pruning.behavior is ServiceBehavior.DETERMINISTIC
    assert pruning.encounter_aware is False
    assert set(pruning.roles) == {"DPS"}
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(pruning.service_id)
    ) == ("extreme.sustained_dps.generated_frontier",)
    assert "never computes ESO damage" in pruning.notes
    assert "Equal-to-incumbent ceilings" in pruning.notes


def test_sustained_dps_dynamic_axis_inventory_consumes_generated_frontier() -> None:
    inventory = canonical_service_for("extreme_sustained_dps_dynamic_axis_inventory")

    assert inventory is not None
    assert inventory.service_id == "extreme.sustained_dps.dynamic_axes"
    assert inventory.behavior is ServiceBehavior.DETERMINISTIC
    assert inventory.encounter_aware is False
    assert set(inventory.roles) == {"DPS"}
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(inventory.service_id)
    ) == ("extreme.sustained_dps.generated_frontier",)
    assert "pruning remains fail-open" in inventory.notes
