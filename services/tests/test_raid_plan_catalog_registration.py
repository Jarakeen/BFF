from services.service_catalog import SERVICE_CATALOG


def test_raid_plan_repository_is_registered_as_canonical_persistence() -> None:
    descriptor = SERVICE_CATALOG.get("raid_plan.repository")

    assert descriptor is not None
    assert descriptor.domain == "raid_plan"
    assert descriptor.ui_safe is True
    assert "raid_plan_persistence" in descriptor.responsibilities


def test_named_group_effect_projection_is_registered_as_canonical_coverage_service() -> None:
    descriptor = SERVICE_CATALOG.get("coverage.named_group_effect_projection")

    assert descriptor is not None
    assert descriptor.domain == "coverage"
    assert descriptor.ui_safe is True
    assert descriptor.encounter_aware is False
    assert "raid_named_group_effect_static_projection" in descriptor.responsibilities
    assert "self-only" in descriptor.notes
    assert "fail closed" in descriptor.notes


def test_readiness_dependency_points_to_registered_raid_plan_coverage_scope() -> None:
    readiness = SERVICE_CATALOG.get("raid.readiness.evidence")
    coverage = SERVICE_CATALOG.get("raid_plan.coverage_scope")

    assert readiness is not None
    assert coverage is not None
    assert "raid_plan.coverage_scope" in readiness.dependencies
    assert "coverage.raid_plan.scope" not in readiness.dependencies
