from services.service_catalog import SERVICE_CATALOG


def test_raid_plan_repository_is_registered_as_canonical_persistence() -> None:
    descriptor = SERVICE_CATALOG.get("raid_plan.repository")

    assert descriptor is not None
    assert descriptor.domain == "raid_plan"
    assert descriptor.ui_safe is True
    assert "raid_plan_persistence" in descriptor.responsibilities
