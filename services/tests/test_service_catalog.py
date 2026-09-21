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
    get_service,
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


def test_sustained_dps_rotation_upper_bound_is_arithmetic_authority() -> None:
    ceiling = canonical_service_for("extreme_sustained_dps_rotation_upper_bound")

    assert ceiling is not None
    assert ceiling.service_id == "extreme.sustained_dps.rotation_upper_bound"
    assert ceiling.behavior is ServiceBehavior.DETERMINISTIC
    assert ceiling.encounter_aware is False
    assert set(ceiling.roles) == {"DPS"}
    assert SERVICE_CATALOG.dependencies_of(ceiling.service_id) == ()
    assert "does not calculate ESO damage" in ceiling.notes
    assert "periodic" in ceiling.notes
    assert "triggered" in ceiling.notes


def test_sustained_dps_action_upper_bound_requires_mutation_dominance() -> None:
    service = canonical_service_for("extreme_sustained_dps_action_upper_bound_promotion")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.action_upper_bound"
    assert service.behavior is ServiceBehavior.DETERMINISTIC
    assert service.encounter_aware is False
    assert set(service.roles) == {"DPS"}
    assert SERVICE_CATALOG.dependencies_of(service.service_id) == ()
    assert "not automatically an upper bound" in service.notes
    assert "fail-open" in service.notes


def test_sustained_dps_mundus_provisioning_dominance_consumes_dynamic_axes() -> None:
    service = canonical_service_for("extreme_sustained_dps_mundus_provisioning_dominance")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.mundus_provisioning_dominance"
    assert service.behavior is ServiceBehavior.DETERMINISTIC
    assert service.encounter_aware is False
    assert set(service.roles) == {"DPS"}
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.dynamic_axes",)
    assert "full joint finite grid" in service.notes
    assert "fail-open" in service.notes


def test_sustained_dps_armor_trait_enchant_frontier_consumes_dynamic_axes() -> None:
    service = canonical_service_for("extreme_sustained_dps_armor_trait_enchant_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.armor_trait_enchant_frontier"
    assert service.behavior is ServiceBehavior.DETERMINISTIC
    assert service.encounter_aware is False
    assert set(service.roles) == {"DPS"}
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.dynamic_axes",)
    assert "full modeled denominator lazily" in service.notes


def test_sustained_dps_equipment_frontiers_are_canonical_axes() -> None:
    jewelry = canonical_service_for("extreme_sustained_dps_jewelry_frontier")
    weapon = canonical_service_for("extreme_sustained_dps_weapon_frontier")

    assert jewelry is not None
    assert weapon is not None
    assert jewelry.service_id == "extreme.sustained_dps.jewelry_frontier"
    assert weapon.service_id == "extreme.sustained_dps.weapon_frontier"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(jewelry.service_id)
    ) == ("extreme.sustained_dps.dynamic_axes",)
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(weapon.service_id)
    ) == ("extreme.sustained_dps.dynamic_axes",)
    assert "runtime-owned" in weapon.notes


def test_sustained_dps_champion_point_frontier_uses_canonical_loadout_legality() -> None:
    service = canonical_service_for("extreme_sustained_dps_champion_point_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.champion_point_frontier"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("mechanics.champion_point_loadout",)
    assert "four-slots-per-discipline" in service.purpose
    assert "Dynamic/runtime" in service.notes


def test_sustained_dps_gear_topology_and_realization_are_separate_authorities() -> None:
    topology = canonical_service_for("extreme_sustained_dps_gear_topology_frontier")
    realization = canonical_service_for("extreme_sustained_dps_gear_topology_realization")

    assert topology is not None
    assert realization is not None
    assert topology.service_id == "extreme.sustained_dps.gear_topology_frontier"
    assert realization.service_id == "extreme.sustained_dps.gear_topology_realization"
    assert SERVICE_CATALOG.dependencies_of(topology.service_id) == ()
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(realization.service_id)
    ) == ("extreme.sustained_dps.gear_topology_frontier",)
    assert "abstract active-snapshot count topology" in topology.notes
    assert "proven-empty branch" in realization.notes


def test_sustained_dps_dual_bar_gear_frontier_requires_realized_topologies() -> None:
    service = canonical_service_for("extreme_sustained_dps_dual_bar_gear_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.dual_bar_gear_frontier"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.gear_topology_realization",)
    assert "complete topology-branch coverage" in service.notes
    assert "bar-access rules" in service.notes


def test_sustained_dps_gear_runtime_semantics_reuses_canonical_resolvers() -> None:
    service = canonical_service_for("extreme_sustained_dps_gear_runtime_semantics")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.gear_runtime_semantics"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.dual_bar_gear_frontier",)
    assert "GearSetEffectResolver" in service.notes
    assert "does not prove proc occurrence" in service.notes


def test_generated_sustained_dps_runtime_evaluation_consumes_canonical_simulation() -> None:
    service = canonical_service_for("extreme_sustained_dps_generated_runtime_evaluation")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_runtime_evaluation"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.gear_runtime_semantics",
        "simulation.saved_build_dd",
    )
    assert "caller-owned" in service.notes
    assert "fail closed" in service.notes


def test_sustained_dps_runtime_effect_projection_is_not_a_timing_authority() -> None:
    service = canonical_service_for("extreme_sustained_dps_runtime_effect_projection")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.runtime_effect_projection"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.gear_runtime_semantics",)
    assert "no trigger, timing, cooldown" in service.notes.casefold()
    assert "weapon_spell_damage" in service.notes


def test_sustained_dps_potion_and_passive_frontiers_preserve_ownership_boundaries() -> None:
    potion = canonical_service_for("extreme_sustained_dps_potion_frontier")
    passive = canonical_service_for("extreme_sustained_dps_passive_rank_frontier")

    assert potion is not None
    assert passive is not None
    assert potion.service_id == "extreme.sustained_dps.potion_frontier"
    assert passive.service_id == "extreme.sustained_dps.passive_rank_frontier"
    assert SERVICE_CATALOG.dependencies_of(potion.service_id) == ()
    assert SERVICE_CATALOG.dependencies_of(passive.service_id) == ()
    assert "Medicinal Use remain runtime-owned" in potion.notes
    assert "shared line ownership must already be explicit" in passive.notes
    assert "Racial passive progression remains race-owned" in passive.notes


def test_sustained_dps_skill_bar_frontier_preserves_morph_and_ownership_denominator() -> None:
    service = canonical_service_for("extreme_sustained_dps_skill_bar_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.skill_bar_frontier"
    assert SERVICE_CATALOG.dependencies_of(service.service_id) == ()
    assert "base/morph alternatives" in service.notes
    assert "explicit shared-line ownership" in service.notes
    assert "Normal-slot permutations are collapsed" in service.notes


def test_sustained_dps_cross_axis_composition_keeps_context_and_assembly_separate() -> None:
    context = canonical_service_for("extreme_sustained_dps_cross_axis_context")
    assembly = canonical_service_for("extreme_sustained_dps_generated_candidate_assembly")

    assert context is not None
    assert assembly is not None
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(context.service_id)
    ) == ("extreme.sustained_dps.dual_bar_gear_frontier",)
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(assembly.service_id)
    ) == (
        "extreme.sustained_dps.cross_axis_context",
        "extreme.sustained_dps.champion_point_frontier",
        "extreme.sustained_dps.potion_frontier",
        "extreme.sustained_dps.passive_rank_frontier",
        "extreme.sustained_dps.skill_bar_frontier",
    )
    assert "subclass route lines" in context.notes
    assert "Each axis contributes only the state it owns" in assembly.notes


def test_sustained_dps_rotation_plan_frontier_is_seed_family_not_policy_closure() -> None:
    service = canonical_service_for("extreme_sustained_dps_rotation_plan_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.rotation_plan_frontier"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.generated_candidate_assembly",)
    assert "ordinary-skill ordering" in service.notes
    assert "Light-Attack weave on/off" in service.notes
    assert "remain separate open axes" in service.notes


def test_sustained_dps_rotation_policy_frontier_keeps_mechanics_authorities_external() -> None:
    service = canonical_service_for("extreme_sustained_dps_rotation_policy_frontier")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.rotation_policy_frontier"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.rotation_plan_frontier",)
    assert "RotationUltimateService" in service.notes
    assert "RotationScheduledActionResourceLegalityService" in service.notes
    assert "continuous potion offsets" in service.notes
    assert "post-affordability Ultimate delays" in service.notes


def test_sustained_dps_execute_and_heavy_policy_frontiers_keep_mechanics_external() -> None:
    execute = canonical_service_for("extreme_sustained_dps_execute_policy_frontier")
    heavy = canonical_service_for("extreme_sustained_dps_heavy_attack_policy_frontier")

    assert execute is not None
    assert heavy is not None
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(execute.service_id)
    ) == ("extreme.sustained_dps.rotation_policy_frontier",)
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(heavy.service_id)
    ) == ("extreme.sustained_dps.rotation_policy_frontier",)
    assert "Does not infer execute superiority" in execute.notes
    assert "1.8s windows" in heavy.notes
    assert "RotationCandidateHeavyAttackDamageEvidenceService" in heavy.notes


def test_sustained_dps_generated_branch_and_bound_keeps_bounds_and_damage_external() -> None:
    search = canonical_service_for("extreme_sustained_dps_generated_branch_and_bound")
    adapter = canonical_service_for("extreme_sustained_dps_generated_search_evidence_adapter")

    assert search is not None
    assert adapter is not None
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(search.service_id)
    ) == ("extreme.sustained_dps.pruning",)
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(adapter.service_id)
    ) == (
        "extreme.sustained_dps.generated_branch_and_bound",
        "extreme.sustained_dps.generated_runtime_evaluation",
    )
    assert "never calculates ESO damage" in search.notes
    assert "Equal ceilings remain open" in search.notes
    assert "Proof-preserving adapter only" in adapter.notes


def test_sustained_dps_partial_branch_upper_bound_intersects_without_double_counting() -> None:
    service = canonical_service_for("extreme_sustained_dps_partial_branch_upper_bound")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.partial_branch_upper_bound"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.pruning",)
    assert "intersected with min()" in service.notes
    assert "never summed" in service.notes
    assert "cannot weaken an inherited proven parent ceiling" in service.notes


def test_sustained_dps_structural_action_bound_requires_external_complete_proofs() -> None:
    service = canonical_service_for("extreme_sustained_dps_structural_action_upper_bound")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.structural_action_upper_bound"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.pruning",)
    assert "infers no ESO action rate or damage formula" in service.notes
    assert "direct, periodic, and triggered consequences" in service.notes


def test_sustained_dps_rotation_family_action_count_proof_avoids_permutation_materialization() -> None:
    service = canonical_service_for("extreme_sustained_dps_rotation_family_action_count_proof")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.rotation_family_action_count_proof"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.rotation_plan_frontier",)
    assert "Skill permutation does not change the cycle shape" in service.notes
    assert "Weave-on is included" in service.notes
    assert "must supply its own proven count ceiling" in service.notes


def test_sustained_dps_ultimate_added_action_count_proof_uses_canonical_affordability_capacity() -> None:
    service = canonical_service_for("extreme_sustained_dps_ultimate_added_action_count_proof")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.ultimate_added_action_count_proof"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.rotation_policy_frontier",)
    assert "UltimateResourceTimeline" in service.notes
    assert "not a claim that every cast occurs" in service.notes


def test_sustained_dps_closed_descendant_action_ceiling_requires_local_denominator_closure() -> None:
    service = canonical_service_for("extreme_sustained_dps_closed_descendant_action_ceiling")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.closed_descendant_action_ceiling"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.structural_action_upper_bound",)
    assert "every descendant and every damage-bearing action" in service.notes
    assert "direct/periodic/triggered completeness" in service.notes
    assert "never extrapolated outward" in service.notes

def test_sustained_dps_generated_frontier_wiring_keeps_authorities_external() -> None:
    service = canonical_service_for("extreme_sustained_dps_generated_frontier_wiring")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_frontier_wiring"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.partial_branch_upper_bound",
        "extreme.sustained_dps.generated_branch_and_bound",
    )
    assert "without materializing" in service.purpose
    assert "legality" in service.notes
    assert "exact Combat Simulation remain external" in service.notes



def test_sustained_dps_axis_dominance_composition_separates_coverage_from_numeric_bounds() -> None:
    service = canonical_service_for("extreme_sustained_dps_axis_dominance_composition")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.axis_dominance_composition"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.action_upper_bound",)
    assert "canonical axis vocabulary" in service.notes
    assert "numeric optimistic multipliers/absolute ceilings" in service.notes
    assert "Missing required axes" in service.notes

def test_sustained_dps_late_axis_adapter_preserves_frontier_authority() -> None:
    service = canonical_service_for("extreme_sustained_dps_generated_late_axis_adapter")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_late_axis_adapter"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.champion_point_frontier",
        "extreme.sustained_dps.potion_frontier",
        "extreme.sustained_dps.passive_rank_frontier",
        "extreme.sustained_dps.skill_bar_frontier",
        "extreme.sustained_dps.generated_candidate_assembly",
        "extreme.sustained_dps.generated_frontier_wiring",
    )
    assert "axis-owned state" in service.notes
    assert "fail closed" in service.notes



def test_sustained_dps_mundus_provisioning_adapter_preserves_joint_dominance() -> None:
    service = canonical_service_for("extreme_sustained_dps_mundus_provisioning_proof_adapter")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.mundus_provisioning_proof_adapter"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.mundus_provisioning_dominance",
        "extreme.sustained_dps.axis_dominance_composition",
    )
    assert "one coupled proof" in service.notes
    assert "promote neither canonical axis coverage nor numeric action ceiling" in service.notes

def test_sustained_dps_generated_gear_axis_adapter_preserves_evolving_build() -> None:
    service = canonical_service_for("extreme_sustained_dps_generated_gear_axis_adapter")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_gear_axis_adapter"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.dual_bar_gear_frontier",
        "extreme.sustained_dps.armor_trait_enchant_frontier",
        "extreme.sustained_dps.jewelry_frontier",
        "extreme.sustained_dps.weapon_frontier",
        "extreme.sustained_dps.cross_axis_context",
        "extreme.sustained_dps.generated_frontier_wiring",
    )
    assert "same evolving materialized build" in service.notes
    assert "fail closed" in service.notes

def test_sustained_dps_generated_rotation_axis_adapter_preserves_proof_scope() -> None:
    service = canonical_service_for(
        "extreme_sustained_dps_generated_rotation_axis_adapter"
    )

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_rotation_axis_adapter"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.rotation_plan_frontier",
        "extreme.sustained_dps.rotation_policy_frontier",
        "extreme.sustained_dps.generated_frontier_wiring",
    )
    assert "plan-before-policy dependency" in service.notes
    assert "does not claim closure" in service.notes



def test_sustained_dps_gear_progression_axis_coverage_promotes_only_proven_structural_axes() -> None:
    service = canonical_service_for("extreme_sustained_dps_gear_progression_axis_coverage")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.gear_progression_axis_coverage"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == ("extreme.sustained_dps.axis_dominance_composition",)
    assert "gear_topology + named_gear_realization" in service.notes
    assert "CP covers champion_points" in service.notes
    assert "passive search covers passive_ranks" in service.notes
    assert "numeric damage dominance remain separate proof obligations" in service.notes

def test_sustained_dps_generated_runtime_policy_adapter_requires_explicit_evidence() -> None:
    service = canonical_service_for(
        "extreme_sustained_dps_generated_runtime_policy_axis_adapter"
    )

    assert service is not None
    assert (
        service.service_id
        == "extreme.sustained_dps.generated_runtime_policy_axis_adapter"
    )
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.execute_policy_frontier",
        "extreme.sustained_dps.heavy_attack_policy_frontier",
        "extreme.sustained_dps.generated_frontier_wiring",
    )
    assert service.encounter_aware is True
    assert "explicit priorities" in service.notes
    assert "do not establish broader theoretical" in service.notes

def test_sustained_dps_generated_axis_pipeline_composes_adapter_states() -> None:
    service = canonical_service_for(
        "extreme_sustained_dps_generated_axis_pipeline"
    )

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.generated_axis_pipeline"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.generated_gear_axis_adapter",
        "extreme.sustained_dps.generated_late_axis_adapter",
        "extreme.sustained_dps.generated_rotation_axis_adapter",
        "extreme.sustained_dps.generated_runtime_policy_axis_adapter",
        "extreme.sustained_dps.generated_frontier_wiring",
    )
    assert service.encounter_aware is True
    assert "reset downstream selections" in service.notes
    assert "axis-local bound providers" in service.notes

def test_sustained_dps_pipeline_leaf_bridge_uses_final_runtime_plan() -> None:
    service = canonical_service_for(
        "extreme_sustained_dps_generated_axis_pipeline_leaf_evaluation"
    )

    assert service is not None
    assert (
        service.service_id
        == "extreme.sustained_dps.generated_axis_pipeline_leaf_evaluation"
    )
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.generated_axis_pipeline",
        "extreme.sustained_dps.generated_runtime_evaluation",
        "extreme.sustained_dps.generated_search_evidence_adapter",
    )
    assert "final downstream runtime-policy plan" in service.notes
    assert "without invoking simulation" in service.notes

def test_sustained_dps_generated_axis_pipeline_search_shares_scenario() -> None:
    service = canonical_service_for(
        "extreme_sustained_dps_generated_axis_pipeline_search"
    )

    assert service is not None
    assert (
        service.service_id
        == "extreme.sustained_dps.generated_axis_pipeline_search"
    )
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.generated_axis_pipeline",
        "extreme.sustained_dps.generated_axis_pipeline_leaf_evaluation",
        "extreme.sustained_dps.generated_frontier_wiring",
        "extreme.sustained_dps.generated_branch_and_bound",
    )
    assert "All exact leaves share" in service.notes
    assert "missing bounds force refinement" in service.notes



def test_sustained_dps_finite_axis_action_dominance_requires_complete_same_coordinate_evidence() -> None:
    direct = get_service("extreme.sustained_dps.finite_axis_action_dominance")
    service = canonical_service_for("extreme_sustained_dps_finite_axis_action_dominance")

    assert direct is not None
    assert service is not None
    assert direct is service
    assert service.service_id == "extreme.sustained_dps.finite_axis_action_dominance"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.axis_dominance_composition",
        "extreme.sustained_dps.structural_action_upper_bound",
    )
    assert "same scheduled action coordinate" in service.notes
    assert "promote neither axis coverage nor numeric ceiling" in service.notes


def test_sustained_dps_finite_axis_frontier_adapter_preserves_lazy_denominator_identity() -> None:
    service = canonical_service_for("extreme_sustained_dps_finite_axis_frontier_adapter")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.finite_axis_frontier_adapter"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.champion_point_frontier",
        "extreme.sustained_dps.passive_rank_frontier",
        "extreme.sustained_dps.dual_bar_gear_frontier",
        "extreme.sustained_dps.finite_axis_action_dominance",
    )
    assert "choice_count + choice_at(index)" in service.notes
    assert "materialized one at a time" in service.notes


def test_sustained_dps_finite_axis_canonical_action_evaluator_delegates_damage_authority() -> None:
    service = canonical_service_for("extreme_sustained_dps_finite_axis_canonical_action_evaluator")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.finite_axis_canonical_action_evaluator"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "simulation.saved_build_dd",
        "extreme.sustained_dps.finite_axis_frontier_adapter",
    )
    assert "Owns adaptation only, not ESO damage math" in service.notes
    assert "Unresolved runtime mechanics remain fail-closed" in service.notes


def test_sustained_dps_finite_family_dominance_search_is_composition_only() -> None:
    service = canonical_service_for("extreme_sustained_dps_finite_family_dominance_search")

    assert service is not None
    assert service.service_id == "extreme.sustained_dps.finite_family_dominance_search"
    assert tuple(
        row.service_id
        for row in SERVICE_CATALOG.dependencies_of(service.service_id)
    ) == (
        "extreme.sustained_dps.finite_axis_frontier_adapter",
        "extreme.sustained_dps.finite_axis_canonical_action_evaluator",
        "extreme.sustained_dps.finite_axis_action_dominance",
    )
    assert "Composition only" in service.notes
    assert "damage remains owned by the canonical DD provider stack" in service.notes
