from __future__ import annotations

from collections import Counter

# Import the canonical catalog first. Its bootstrap owns descriptor-family loading;
# importing an extension descriptor module first would invert that dependency.
from services.service_catalog import SERVICE_CATALOG
from services.application_catalog_descriptors import APPLICATION_SERVICE_DESCRIPTORS
from services.comp_maker_catalog_descriptors import COMP_MAKER_SERVICE_DESCRIPTORS
from services.rotation_catalog_descriptors import ROTATION_SERVICE_DESCRIPTORS
from services.team_prescription_catalog_descriptors import (
    TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
)
from services.team_provider_catalog_descriptors import TEAM_PROVIDER_SERVICE_DESCRIPTORS
from services.team_workflow_catalog_descriptors import TEAM_WORKFLOW_SERVICE_DESCRIPTORS


EXPORTED_DESCRIPTOR_FAMILIES = {
    "application": APPLICATION_SERVICE_DESCRIPTORS,
    "comp_maker": COMP_MAKER_SERVICE_DESCRIPTORS,
    "rotation": ROTATION_SERVICE_DESCRIPTORS,
    "team_prescription": TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
    "team_provider": TEAM_PROVIDER_SERVICE_DESCRIPTORS,
    "team_workflow": TEAM_WORKFLOW_SERVICE_DESCRIPTORS,
}


def test_every_exported_descriptor_family_reaches_canonical_catalog() -> None:
    catalog_ids = {descriptor.service_id for descriptor in SERVICE_CATALOG.descriptors}

    missing_by_family = {
        family_name: sorted(
            descriptor.service_id
            for descriptor in descriptors
            if descriptor.service_id not in catalog_ids
        )
        for family_name, descriptors in EXPORTED_DESCRIPTOR_FAMILIES.items()
    }
    missing_by_family = {
        family_name: missing
        for family_name, missing in missing_by_family.items()
        if missing
    }

    assert missing_by_family == {}


def test_canonical_catalog_service_ids_are_globally_unique() -> None:
    counts = Counter(
        descriptor.service_id for descriptor in SERVICE_CATALOG.descriptors
    )
    duplicates = sorted(
        service_id for service_id, count in counts.items() if count > 1
    )

    assert duplicates == []


def test_canonical_catalog_dependencies_resolve_to_registered_services() -> None:
    catalog_ids = {descriptor.service_id for descriptor in SERVICE_CATALOG.descriptors}
    unresolved = {
        descriptor.service_id: sorted(
            dependency_id
            for dependency_id in descriptor.dependencies
            if dependency_id not in catalog_ids
        )
        for descriptor in SERVICE_CATALOG.descriptors
    }
    unresolved = {
        service_id: dependency_ids
        for service_id, dependency_ids in unresolved.items()
        if dependency_ids
    }

    assert unresolved == {}


def test_canonical_catalog_implementation_paths_are_nonblank() -> None:
    invalid = sorted(
        descriptor.service_id
        for descriptor in SERVICE_CATALOG.descriptors
        if not descriptor.implementation_path.strip()
    )

    assert invalid == []


def test_application_registry_descriptors_are_queryable_by_original_ids() -> None:
    for descriptor in APPLICATION_SERVICE_DESCRIPTORS:
        registered = SERVICE_CATALOG.get(descriptor.service_id)
        assert registered is not None
        assert registered.service_id == descriptor.service_id
