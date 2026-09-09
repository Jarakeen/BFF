from __future__ import annotations

import pytest

from services.service_catalog import (
    CapabilityStatus,
    EvidenceClass,
    SERVICE_CATALOG,
    ServiceAuthority,
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
