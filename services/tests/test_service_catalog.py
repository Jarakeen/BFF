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
